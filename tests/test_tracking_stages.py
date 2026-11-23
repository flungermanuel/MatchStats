"""T4: Stufen detect_stage und track_stage mit Fakes (kleine Bilder, kein Modell, kein Video)."""

from dataclasses import replace

import numpy as np

from matchstats.application.tracking_stages import detect_stage, track_stage
from matchstats.domain.detection import Detection
from matchstats.domain.result import RunResult
from matchstats.domain.settings import Settings
from matchstats.domain.tracking import DetectionsDoc, Track, TrackPoint

VERSIONS = {"fake": "1.0"}
HIGH = Detection(10.0, 10.0, 20.0, 50.0, 0.9)
LOW = Detection(100.0, 10.0, 20.0, 50.0, 0.05)  # unter detect_min_score (0,1)


class FakeSource:
    name = "clip.mp4"
    fps = 25.0
    frame_count = 23
    frame_size = (64, 36)

    def __init__(self) -> None:
        self.requested_every: list[int] = []

    def frames(self, every: int):
        self.requested_every.append(every)
        for index in range(self.frame_count):
            if index % every == 0:
                yield index, np.zeros((36, 64, 3), dtype=np.uint8)


class FakeDetector:
    def __init__(self) -> None:
        self.calls = 0

    def detect(self, image: np.ndarray) -> list[Detection]:
        self.calls += 1
        return [HIGH, LOW]


class MemoryStore:
    def __init__(self) -> None:
        self.detections: DetectionsDoc | None = None
        self.tracks: list[RunResult] = []

    def load_detections(self):
        return self.detections

    def save_detections(self, doc: DetectionsDoc) -> None:
        self.detections = doc

    def save_tracks(self, result: RunResult) -> None:
        self.tracks.append(result)


class FakeTracker:
    def __init__(self) -> None:
        self.args = None

    def track(self, frames, frame_count, frame_size, camera=None):
        # camera: seit T4b reicht track_stage den Kamerapfad mit durch
        self.args = (list(frames), frame_count, frame_size)
        point = TrackPoint(0, 1.0, 2.0, 3.0, 4.0, True, 0.9)
        return [Track(id=1, points=(point,))]


def _detect(settings=None, name="rfdetr-small-whole", store=None, detector=None, source=None):
    settings = settings or Settings()
    store = store if store is not None else MemoryStore()
    detector = detector or FakeDetector()
    source = source or FakeSource()
    doc, reused = detect_stage(source, detector, name, settings, store, VERSIONS)
    return doc, reused, detector, source, store


# --- detect_stage ---


def test_detection_runs_only_on_every_nth_frame():
    doc, reused, detector, source, _ = _detect(Settings(detect_every=5))

    assert reused is False
    assert source.requested_every == [5]
    assert detector.calls == 5  # Bilder 0, 5, 10, 15, 20 von 23
    assert [f.frame for f in doc.frames] == [0, 5, 10, 15, 20]


def test_detection_document_describes_the_clip_and_the_run():
    doc, _, _, _, store = _detect()

    assert (doc.source, doc.fps, doc.frame_count, doc.frame_size) == (
        "clip.mp4",
        25.0,
        23,
        (64, 36),
    )
    assert doc.detector == "rfdetr-small-whole"
    assert doc.versions == VERSIONS
    assert store.detections == doc


def test_detections_below_detect_min_score_are_not_stored():
    doc, *_ = _detect(Settings(detect_min_score=0.1))

    for frame in doc.frames:
        assert frame.detections == (HIGH,)


def test_detect_min_score_of_zero_point_zero_five_keeps_the_weak_detection():
    doc, *_ = _detect(Settings(detect_min_score=0.05))

    assert all(len(f.detections) == 2 for f in doc.frames)


def test_stage_params_name_everything_that_determines_the_result():
    settings = Settings()

    doc, *_ = _detect(settings)

    assert doc.stage_params == {
        "detector": "rfdetr-small-whole",
        "detect_every": settings.detect_every,
        "detect_min_score": settings.detect_min_score,
        "detector_model": settings.detector_model,
        "tile_size": settings.tile_size,
        "tile_overlap": settings.tile_overlap,
        "nms_iou": settings.nms_iou,
    }


def test_detections_are_reused_when_stage_params_are_equal_without_calling_the_detector():
    first_doc, _, _, _, store = _detect()
    second_detector = FakeDetector()

    doc, reused, _, source, _ = _detect(store=store, detector=second_detector)

    assert reused is True
    assert doc == first_doc
    assert second_detector.calls == 0
    assert source.requested_every == []  # das Video wird gar nicht gelesen


def test_detections_are_recomputed_when_detect_every_changes():
    _, _, _, _, store = _detect(Settings(detect_every=5))
    detector = FakeDetector()

    doc, reused, *_ = _detect(Settings(detect_every=10), store=store, detector=detector)

    assert reused is False
    assert detector.calls == 3  # Bilder 0, 10, 20
    assert doc.stage_params["detect_every"] == 10
    assert store.detections == doc  # neue Datei ersetzt die alte


def test_detections_are_recomputed_when_the_detector_name_changes():
    _, _, _, _, store = _detect(name="rfdetr-small-whole")
    detector = FakeDetector()

    doc, reused, *_ = _detect(name="rfdetr-small-tiles", store=store, detector=detector)

    assert reused is False
    assert detector.calls == 5
    assert doc.detector == "rfdetr-small-tiles"


def test_detections_are_recomputed_when_detect_min_score_changes():
    _, _, _, _, store = _detect(Settings(detect_min_score=0.1))
    detector = FakeDetector()

    _, reused, *_ = _detect(Settings(detect_min_score=0.2), store=store, detector=detector)

    assert reused is False
    assert detector.calls == 5


def test_detections_are_recomputed_when_the_stored_file_is_missing():
    store = MemoryStore()  # load_detections() -> None

    _, reused, detector, *_ = _detect(store=store)

    assert reused is False
    assert detector.calls == 5


# --- track_stage ---


def _doc() -> DetectionsDoc:
    doc, *_ = _detect()
    return doc


def test_track_stage_returns_result_with_schema_version_2_and_clip_data():
    doc = _doc()
    store = MemoryStore()

    result = track_stage(doc, FakeTracker(), Settings(), store, VERSIONS)

    assert result.schema_version == 2
    assert result.source == "clip.mp4"
    assert (result.fps, result.frame_count) == (25.0, 23)
    assert result.versions == VERSIONS
    assert len(result.tracks) == 1 and result.tracks[0].id == 1
    assert result.settings["detect_every"] == 5


def test_track_stage_hands_frames_count_and_size_to_the_tracker():
    doc = _doc()
    tracker = FakeTracker()

    track_stage(doc, tracker, Settings(), MemoryStore(), VERSIONS)

    frames, frame_count, frame_size = tracker.args
    assert tuple(frames) == doc.frames
    assert (frame_count, frame_size) == (23, (64, 36))


def test_track_stage_always_saves_and_never_reuses_an_earlier_result():
    doc = _doc()
    store = MemoryStore()
    tracker = FakeTracker()

    track_stage(doc, tracker, Settings(), store, VERSIONS)
    track_stage(replace(doc), tracker, Settings(), store, VERSIONS)

    assert len(store.tracks) == 2


# --- Cache-Schlüssel: Video darf nicht ausgetauscht worden sein ---


def _changed_source(**attrs):
    source = FakeSource()
    for name, value in attrs.items():
        setattr(source, name, value)
    return source


def test_detections_are_recomputed_when_the_video_file_name_changed():
    _, _, _, _, store = _detect()
    detector = FakeDetector()

    _, reused, *_ = _detect(store=store, detector=detector, source=_changed_source(name="neu.mp4"))

    assert reused is False
    assert detector.calls == 5


def test_detections_are_recomputed_when_the_frame_count_changed():
    _, _, _, _, store = _detect()
    detector = FakeDetector()

    _, reused, *_ = _detect(store=store, detector=detector, source=_changed_source(frame_count=40))

    assert reused is False
    assert detector.calls == 8  # Bilder 0, 5, ..., 35


def test_detections_are_recomputed_when_the_frame_size_changed():
    _, _, _, _, store = _detect()
    detector = FakeDetector()

    _, reused, *_ = _detect(
        store=store, detector=detector, source=_changed_source(frame_size=(128, 72))
    )

    assert reused is False
    assert detector.calls == 5
