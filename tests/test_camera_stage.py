"""T4b: camera_stage und Durchreichen des Kamerapfads in track_stage (Fakes, kein Video)."""

from dataclasses import replace

import numpy as np
from matchstats.domain.camera import IDENTITY, NO_CAMERA, CameraDoc, CameraMotion, CameraPath

from matchstats.application.tracking_stages import camera_stage, track_stage
from matchstats.domain.result import RunResult
from matchstats.domain.settings import Settings
from matchstats.domain.tracking import DetectionsDoc, Track, TrackPoint

VERSIONS = {"fake": "1.0"}


class FakeSource:
    name = "clip.mp4"
    fps = 25.0
    frame_count = 6
    frame_size = (64, 36)

    def __init__(self) -> None:
        self.requested_every: list[int] = []

    def frames(self, every: int):
        self.requested_every.append(every)
        for index in range(self.frame_count):
            if index % every == 0:
                yield index, np.zeros((36, 64, 3), dtype=np.uint8)


class FakeEstimator:
    def __init__(self) -> None:
        self.calls = 0
        self.seen_indices: list[int] = []

    def estimate(self, images):
        self.calls += 1
        motions = []
        for index, _image in images:
            self.seen_indices.append(index)
            if index >= 1:
                motions.append(CameraMotion(index, IDENTITY, 1.0))
        return motions


class MemoryStore:
    def __init__(self) -> None:
        self.camera: CameraDoc | None = None
        self.tracks: list[RunResult] = []

    def load_camera(self):
        return self.camera

    def save_camera(self, doc: CameraDoc) -> None:
        self.camera = doc

    def save_tracks(self, result: RunResult) -> None:
        self.tracks.append(result)


def _run(settings=None, store=None, estimator=None, source=None):
    settings = settings or Settings()
    store = store if store is not None else MemoryStore()
    estimator = estimator or FakeEstimator()
    source = source or FakeSource()
    doc, reused = camera_stage(source, estimator, settings, store, VERSIONS)
    return doc, reused, estimator, source, store


def test_camera_stage_reads_every_frame_and_stores_one_motion_per_frame_from_index_one():
    doc, reused, estimator, source, store = _run()

    assert reused is False
    assert source.requested_every == [1]
    assert estimator.seen_indices == [0, 1, 2, 3, 4, 5]
    assert [m.frame for m in doc.motions] == [1, 2, 3, 4, 5]
    assert store.camera == doc


def test_camera_document_describes_the_clip_and_the_stage_parameters():
    settings = Settings()

    doc, *_ = _run(settings)

    assert (doc.source, doc.fps, doc.frame_count, doc.frame_size) == ("clip.mp4", 25.0, 6, (64, 36))
    assert doc.versions == VERSIONS
    assert doc.stage_params == {
        "camera_downscale": settings.camera_downscale,
        "camera_min_quality": settings.camera_min_quality,
        "camera_max_features": settings.camera_max_features,
    }


def test_camera_stage_reuses_saved_estimate_when_video_and_params_match():
    first_doc, _, _, _, store = _run()
    second_estimator = FakeEstimator()

    doc, reused, _, source, _ = _run(store=store, estimator=second_estimator)

    assert reused is True
    assert doc == first_doc
    assert second_estimator.calls == 0
    assert source.requested_every == []  # das Video wird gar nicht gelesen


def test_camera_stage_recomputes_when_params_change():
    _, _, _, _, store = _run(Settings(camera_downscale=1.0))
    estimator = FakeEstimator()

    doc, reused, *_ = _run(Settings(camera_downscale=0.5), store=store, estimator=estimator)

    assert reused is False
    assert estimator.calls == 1
    assert doc.stage_params["camera_downscale"] == 0.5
    assert store.camera == doc  # neue Datei ersetzt die alte


def test_camera_stage_recomputes_when_min_quality_or_max_features_change():
    base = Settings()
    _, _, _, _, store = _run(base)

    for changed in (replace(base, camera_min_quality=0.9), replace(base, camera_max_features=50)):
        estimator = FakeEstimator()
        _, reused, *_ = _run(changed, store=store, estimator=estimator)
        assert reused is False
        assert estimator.calls == 1


def test_camera_stage_recomputes_when_the_video_changed():
    _, _, _, _, store = _run()
    other = FakeSource()
    other.name = "neu.mp4"
    estimator = FakeEstimator()

    _, reused, *_ = _run(store=store, estimator=estimator, source=other)

    assert reused is False
    assert estimator.calls == 1


def test_camera_stage_recomputes_when_no_saved_estimate_exists():
    _, reused, estimator, *_ = _run(store=MemoryStore())

    assert reused is False
    assert estimator.calls == 1


# --- track_stage reicht den Kamerapfad durch ---


class RecordingTracker:
    def __init__(self) -> None:
        self.camera = "nicht aufgerufen"

    def track(self, frames, frame_count, frame_size, camera=NO_CAMERA):
        self.camera = camera
        point = TrackPoint(0, 1.0, 2.0, 3.0, 4.0, True, 0.9)
        return [Track(id=1, points=(point,))]


def _detections_doc() -> DetectionsDoc:
    return DetectionsDoc("clip.mp4", "fake", 25.0, 6, (64, 36), {}, VERSIONS, ())


def test_track_stage_hands_the_camera_path_to_the_tracker():
    path = CameraPath(motions=(CameraMotion(1, IDENTITY, 1.0),))
    tracker = RecordingTracker()

    track_stage(_detections_doc(), tracker, Settings(), MemoryStore(), VERSIONS, camera=path)

    assert tracker.camera is path


def test_track_stage_without_camera_argument_runs_without_compensation():
    tracker = RecordingTracker()

    track_stage(_detections_doc(), tracker, Settings(), MemoryStore(), VERSIONS)

    assert tracker.camera == NO_CAMERA
