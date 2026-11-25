"""T5b1: team_stage mit Fakes (Klassifikator, Videoquelle, Speicher); kein Video, kein Modell.

Der Fake-Klassifikator entscheidet nach der Boxbreite (bleibt beim Ausschneiden gleich):
Breite 20 -> team_a, Breite 30 -> team_b, Breite 40 -> unbekannt.
"""

import json
from dataclasses import asdict, replace

import numpy as np
import pytest

from matchstats.application.team_stage import team_params, team_stage
from matchstats.domain.result import RunResult
from matchstats.domain.settings import Settings
from matchstats.domain.teams import UNKNOWN, TeamPrediction, TeamsDoc
from matchstats.domain.tracking import Track, TrackPoint

VERSIONS = {"fake": "1.0"}
LABEL_BY_WIDTH = {20.0: "team_a", 30.0: "team_b", 40.0: None}


class FakeSource:
    name = "clip.mp4"
    fps = 25.0
    frame_count = 100
    frame_size = (64, 36)

    def __init__(self) -> None:
        self.requested_every: list[int] = []
        self.read_indices: list[int] = []

    def frames(self, every: int):
        self.requested_every.append(every)
        for index in range(self.frame_count):
            if index % every == 0:
                self.read_indices.append(index)
                yield index, np.zeros((36, 64, 3), dtype=np.uint8)


class FakeClassifier:
    def __init__(self) -> None:
        self.calls = 0
        self.boxes: list = []

    def classify(self, images, boxes):
        self.calls += 1
        assert len(images) == len(boxes)
        self.boxes.extend(boxes)
        return [TeamPrediction(LABEL_BY_WIDTH[b.w], 0.9) for b in boxes]


class MemoryTeamsStore:
    """Speichert wie die Datei: stage_params laufen durch JSON (Tupel werden zu Listen)."""

    def __init__(self) -> None:
        self.doc: TeamsDoc | None = None
        self.saved = 0

    def load_teams(self):
        return self.doc

    def save_teams(self, doc: TeamsDoc) -> None:
        self.saved += 1
        self.doc = replace(doc, stage_params=json.loads(json.dumps(doc.stage_params)))


def point(frame, w=20.0, visible=True, x=5.0):
    return TrackPoint(frame, x, 4.0, w, 28.0, visible, 0.9 if visible else None)


def track(track_id, w=20.0, frames=range(0, 100, 5), x=5.0):
    return Track(track_id, tuple(point(f, w, x=x) for f in frames))


def make_result(*tracks, settings=None):
    return RunResult(
        source="clip.mp4",
        settings=asdict(settings or Settings()),
        tracks=tuple(tracks),
        fps=25.0,
        frame_count=100,
    )


def run(result, settings=None, store=None, source=None, classifier=None, name="color"):
    settings = settings or Settings()
    store = store if store is not None else MemoryTeamsStore()
    source = source or FakeSource()
    classifier = classifier or FakeClassifier()
    doc, reused = team_stage(result, source, classifier, name, settings, store, VERSIONS)
    return doc, reused, source, classifier, store


def test_one_classify_call_per_clip_with_all_samples_of_all_tracks():
    result = make_result(track(1, 20.0), track(2, 30.0))

    doc, reused, _source, classifier, _store = run(result)

    assert reused is False
    assert classifier.calls == 1
    assert len(classifier.boxes) == 16  # 2 Spuren x 8 Stichproben


def test_track_gets_the_majority_class_of_its_samples():
    doc, *_ = run(make_result(track(1, 20.0), track(2, 30.0)))

    assert [(t.id, t.label) for t in doc.tracks] == [(1, "team_a"), (2, "team_b")]
    assert doc.tracks[0].votes["team_a"] == 8
    assert doc.tracks[0].uncertainty == 0.0


def test_at_most_team_samples_per_track_samples_are_taken():
    settings = replace(Settings(), team_samples_per_track=4)

    doc, _r, _s, classifier, _st = run(make_result(track(1)), settings=settings)

    assert doc.tracks[0].samples == 4
    assert len(classifier.boxes) == 4


def test_short_track_uses_all_its_visible_points_as_samples():
    doc, _r, _s, classifier, _st = run(make_result(track(1, frames=[10, 15, 20])))

    assert doc.tracks[0].samples == 3
    assert len(classifier.boxes) == 3


def test_all_tracks_appear_in_teams_json_in_result_order():
    result = make_result(track(9, 20.0), track(3, 30.0), track(5, 20.0))

    doc, *_ = run(result)

    assert [t.id for t in doc.tracks] == [9, 3, 5]


def test_track_without_visible_points_is_listed_with_zero_samples_and_null_label():
    hidden = Track(4, tuple(point(f, visible=False) for f in (5, 10, 15)))

    doc, _r, _s, classifier, _st = run(make_result(track(1), hidden))

    entry = doc.tracks[1]
    assert entry.id == 4
    assert (entry.samples, entry.label, entry.uncertainty) == (0, None, None)
    assert entry.votes == {"team_a": 0, "team_b": 0, "goalkeeper": 0, "referee": 0, UNKNOWN: 0}
    assert len(classifier.boxes) == 8  # nur die Stichproben der ersten Spur


def test_unknown_predictions_count_as_unknown_votes_not_as_class_votes():
    doc, *_ = run(make_result(track(1, 40.0)))

    assert doc.tracks[0].label is None
    assert doc.tracks[0].votes[UNKNOWN] == 8
    assert doc.tracks[0].samples == 8


def test_team_min_votes_from_settings_controls_the_null_label():
    settings = replace(Settings(), team_min_votes=9)

    doc, *_ = run(make_result(track(1, 20.0)), settings=settings)

    assert doc.tracks[0].label is None  # nur 8 bekannte Stimmen


def test_hidden_points_are_never_read_or_classified():
    points = tuple(point(f) for f in range(0, 50, 5)) + tuple(
        point(f, visible=False, x=999.0) for f in range(50, 100, 5)
    )
    source, classifier = FakeSource(), FakeClassifier()

    run(make_result(Track(1, points)), source=source, classifier=classifier)

    assert all(box.x != 999.0 and box.x < 64 for box in classifier.boxes)
    assert len(classifier.boxes) == 8
    assert max(source.read_indices) <= 45  # nicht über das letzte gesehene Bild hinaus


def test_frame_step_is_gcd_of_selected_frames_and_reading_stops_after_last_needed_frame():
    source = FakeSource()

    run(make_result(track(1, frames=[10, 20, 30])), source=source)

    assert source.requested_every == [10]
    assert max(source.read_indices) == 30


def test_video_is_read_once_per_clip():
    source = FakeSource()

    run(make_result(track(1), track(2, 30.0)), source=source)

    assert len(source.requested_every) == 1


def test_second_run_with_default_settings_reuses_file_and_does_not_read_video():
    store = MemoryTeamsStore()
    result = make_result(track(1), track(2, 30.0))
    first, _r, _s, _c, _st = run(result, store=store)

    source, classifier = FakeSource(), FakeClassifier()
    second, reused, *_ = run(result, store=store, source=source, classifier=classifier)

    assert reused is True
    assert second == first
    assert source.requested_every == []
    assert classifier.calls == 0
    assert store.saved == 1


def test_cache_hit_survives_json_roundtrip_of_tuple_settings():
    params = team_params(Settings(), "color")
    assert json.loads(json.dumps(params)) == params  # Tupel schon als Liste (JSON-fest)
    assert params["classifier"] == "color"
    assert params["team_samples_per_track"] == 8
    assert params["team_min_votes"] == 3
    assert params["team_grass_hue_range"] == [35, 85]
    assert all(key == "classifier" or key.startswith("team_") for key in params)


def test_changed_track_recomputes():
    store = MemoryTeamsStore()
    run(make_result(track(1, x=5.0)), store=store)

    source = FakeSource()
    doc, reused, *_ = run(make_result(track(1, x=6.0)), store=store, source=source)

    assert reused is False
    assert source.requested_every != []
    assert store.saved == 2


def test_changed_visibility_of_a_point_recomputes():
    store = MemoryTeamsStore()
    run(make_result(track(1)), store=store)
    points = track(1).points
    changed = Track(1, (replace(points[0], visible=False), *points[1:]))

    _doc, reused, *_ = run(make_result(changed), store=store)

    assert reused is False


@pytest.mark.parametrize(
    "change",
    [
        {"team_samples_per_track": 5},
        {"team_min_votes": 2},
        {"team_upper_body_fraction": 0.4},
        {"team_cluster_count": 3},
        {"team_grass_hue_range": (30, 80)},
    ],
)
def test_changed_team_setting_recomputes(change):
    store = MemoryTeamsStore()
    result = make_result(track(1))
    run(result, store=store)

    _doc, reused, source, classifier, _st = run(
        result, settings=replace(Settings(), **change), store=store
    )

    assert reused is False
    assert classifier.calls == 1
    assert source.requested_every != []


def test_changed_classifier_name_recomputes():
    store = MemoryTeamsStore()
    result = make_result(track(1))
    run(result, store=store, name="color")

    _doc, reused, *_ = run(result, store=store, name="other")

    assert reused is False


def test_changed_video_identity_recomputes():
    store = MemoryTeamsStore()
    result = make_result(track(1))
    run(result, store=store)
    other = FakeSource()
    other.frame_size = (128, 72)

    _doc, reused, *_ = run(result, store=store, source=other)

    assert reused is False


def test_result_from_other_video_raises_value_error_and_reads_nothing():
    result = replace(make_result(track(1)), source="other.mp4")
    source = FakeSource()

    with pytest.raises(ValueError):
        run(result, source=source)

    assert source.requested_every == []


def test_different_frame_count_raises_value_error():
    result = replace(make_result(track(1)), frame_count=99)

    with pytest.raises(ValueError):
        run(result)


def test_document_carries_video_identity_versions_params_and_fingerprint():
    result = make_result(track(1))

    doc, *_ = run(result)

    assert doc.schema_version == 1
    assert (doc.source, doc.fps, doc.frame_count) == ("clip.mp4", 25.0, 100)
    assert tuple(doc.frame_size) == (64, 36)
    assert doc.versions == VERSIONS
    assert doc.stage_params == team_params(Settings(), "color")
    assert len(doc.tracks_fingerprint) == 64
    assert doc.note
