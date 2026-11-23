"""T4: Kandidaten für ID-Wechsel, automatisch aus den Spuren (kein Handzählen).

Ein Kandidat: Eine Spur endet mitten im Bild, und kurz danach beginnt in der Nähe eine neue.
"""

import pytest

from matchstats.application.track_summary import summarize_id_switch_candidates
from matchstats.domain.id_switch import find_id_switch_candidates
from matchstats.domain.result import RunResult
from matchstats.domain.settings import Settings
from matchstats.domain.tracking import Track, TrackPoint

FPS = 25.0
FRAME_SIZE = (1920, 1080)
FRAME_COUNT = 1500


def _track(track_id: int, first: int, last: int, x: float = 500.0, y: float = 500.0) -> Track:
    points = tuple(
        TrackPoint(frame=i, x=x, y=y, w=20.0, h=50.0, visible=True, score=0.9)
        for i in range(first, last + 1)
    )
    return Track(id=track_id, points=points)


def _find(tracks, settings: Settings | None = None):
    return find_id_switch_candidates(tracks, FPS, FRAME_SIZE, FRAME_COUNT, settings or Settings())


def test_candidate_when_track_ends_and_a_new_one_starts_close_by_soon():
    candidates = _find([_track(1, 100, 200), _track(2, 205, 300, x=510.0)])

    assert len(candidates) == 1
    assert (candidates[0].old_id, candidates[0].new_id) == (1, 2)
    assert (candidates[0].end_frame, candidates[0].start_frame) == (200, 205)


def test_no_candidate_when_the_new_track_starts_too_late():
    # Standard: höchstens 1,0 s (25 Bilder) Lücke; hier 40 Bilder
    assert _find([_track(1, 100, 200), _track(2, 240, 300)]) == ()


def test_no_candidate_when_the_new_track_starts_far_away():
    # Standard: höchstens 1 Boxhöhe (50 px) Abstand; hier 400 px
    assert _find([_track(1, 100, 200), _track(2, 205, 300, x=900.0)]) == ()


def test_no_candidate_when_the_old_track_ends_at_the_image_edge():
    # Das ist ein Austritt aus dem Bild, kein ID-Wechsel
    assert _find([_track(1, 100, 200, x=10.0), _track(2, 205, 300, x=15.0)]) == ()


def test_no_candidate_when_the_old_track_ends_with_the_clip():
    last = FRAME_COUNT - 1
    assert _find([_track(1, 1400, last), _track(2, last, last + 3)]) == ()


def test_no_candidate_when_the_new_track_overlaps_the_old_one_in_time():
    # Zwei Spieler nebeneinander, beide im Bild: kein Wechsel
    assert _find([_track(1, 100, 200), _track(2, 150, 300, x=510.0)]) == ()


def test_one_new_track_is_matched_to_the_nearest_old_track_only():
    old_near = _track(1, 100, 200, x=500.0)
    old_far = _track(2, 100, 200, x=530.0)
    new = _track(3, 205, 300, x=505.0)

    candidates = _find([old_near, old_far, new])

    assert [(c.old_id, c.new_id) for c in candidates] == [(1, 3)]


def test_one_old_track_is_matched_to_one_new_track_only():
    old = _track(1, 100, 200, x=500.0)
    new_near = _track(2, 205, 300, x=505.0)
    new_far = _track(3, 205, 300, x=530.0)

    candidates = _find([old, new_near, new_far])

    assert [(c.old_id, c.new_id) for c in candidates] == [(1, 2)]


def test_gap_threshold_comes_from_settings():
    tracks = [_track(1, 100, 200), _track(2, 240, 300)]  # 40 Bilder Lücke

    assert _find(tracks) == ()
    assert _find(tracks, Settings(switch_max_gap_seconds=2.0)) != ()


def test_distance_threshold_comes_from_settings():
    tracks = [_track(1, 100, 200), _track(2, 205, 300, x=560.0)]  # 60 px = 1,2 Boxhöhen

    assert _find(tracks) == ()
    assert _find(tracks, Settings(switch_max_distance_heights=2.0)) != ()


def test_candidate_at_exactly_the_gap_and_distance_limits():
    # Grenze zählt noch dazu: 25 Bilder (1,0 s) Lücke, genau 1 Boxhöhe (50 px) Abstand
    assert len(_find([_track(1, 100, 200), _track(2, 225, 300, x=550.0)])) == 1


def test_track_without_points_is_ignored():
    assert _find([Track(id=1, points=()), _track(2, 100, 200)]) == ()


def test_summary_counts_candidates_per_track_minute():
    tracks = [_track(1, 100, 199), _track(2, 205, 304, x=510.0)]
    result = RunResult(
        source="clip.mp4", settings={}, tracks=tuple(tracks), fps=FPS, frame_count=FRAME_COUNT
    )

    summary = summarize_id_switch_candidates(result, _find(tracks))

    # 2 Spuren à 100 Bilder = 8 s = 0,1333 Minuten Spurzeit, 1 Kandidat
    assert summary["id_switch_candidates"] == 1
    assert summary["track_minutes"] == pytest.approx(8 / 60)
    assert summary["id_switch_candidates_per_track_minute"] == pytest.approx(7.5)


def test_summary_without_tracks_has_no_invented_rate():
    result = RunResult(source="clip.mp4", settings={}, fps=FPS, frame_count=FRAME_COUNT)

    summary = summarize_id_switch_candidates(result, ())

    assert summary["id_switch_candidates"] == 0
    assert summary["id_switch_candidates_per_track_minute"] is None
