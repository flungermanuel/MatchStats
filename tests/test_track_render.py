"""track_render: klare Fehlermeldung, wenn das Ausgabevideo nicht geschrieben werden kann."""

import pytest

pytest.importorskip("cv2")

from matchstats.domain.result import RunResult  # noqa: E402
from matchstats.infrastructure import track_render  # noqa: E402


class _ClosedWriter:
    def __init__(self, *args) -> None:
        pass

    def isOpened(self) -> bool:  # noqa: N802 (OpenCV-Name)
        return False

    def release(self) -> None:
        pass


class _Source:
    fps = 25.0
    frame_size = (64, 36)
    name = "clip.mp4"
    frame_count = 1

    def frames(self, every):
        raise AssertionError("darf nicht gelesen werden")


def test_render_raises_when_the_video_writer_cannot_be_opened(tmp_path, monkeypatch):
    monkeypatch.setattr(track_render.cv2, "VideoWriter", _ClosedWriter)
    result = RunResult(source="clip.mp4", settings={}, tracks=(), fps=25.0, frame_count=1)

    with pytest.raises(OSError, match="tracks.mp4"):
        track_render.render_tracks(_Source(), result, tmp_path / "render")


class _VideoSource:
    """Kleine synthetische Videoquelle: graue Bilder, Größe frei wählbar."""

    fps = 25.0
    name = "clip.mp4"

    def __init__(self, size=(640, 360), frame_count=10) -> None:
        self.frame_size = size
        self.frame_count = frame_count

    def frames(self, every):
        import numpy as np

        width, height = self.frame_size
        for index in range(0, self.frame_count, every):
            yield index, np.full((height, width, 3), 120, dtype=np.uint8)


def _track_with_points(track_id, first, last, x):
    from matchstats.domain.tracking import Track, TrackPoint

    points = tuple(
        TrackPoint(frame=i, x=x, y=100.0, w=20.0, h=50.0, visible=True, score=0.9)
        for i in range(first, last + 1)
    )
    return Track(id=track_id, points=points)


def _switch_case(size=(640, 360), x=300.0):
    from matchstats.domain.id_switch import IdSwitchCandidate

    result = RunResult(
        source="clip.mp4",
        settings={},
        tracks=(_track_with_points(1, 0, 3, x), _track_with_points(2, 5, 8, x + 5)),
        fps=25.0,
        frame_count=10,
    )
    candidate = IdSwitchCandidate(
        old_id=1, new_id=2, end_frame=3, start_frame=5, distance_in_heights=0.1
    )
    return _VideoSource(size), result, candidate


def test_render_writes_one_comparison_image_per_id_switch_candidate(tmp_path):
    import cv2

    source, result, candidate = _switch_case()

    track_render.render_tracks(source, result, tmp_path, (candidate,))

    image = cv2.imread(str(tmp_path / "switches" / "switch_001.png"))
    crop_w, crop_h = track_render.SWITCH_CROP
    # links alt, rechts neu: zwei gleich große, vergrößerte Ausschnitte nebeneinander
    assert image.shape[:2] == (
        crop_h * track_render.SWITCH_ZOOM,
        2 * crop_w * track_render.SWITCH_ZOOM,
    )


def test_render_writes_no_comparison_images_without_candidates(tmp_path):
    source, result, _ = _switch_case()

    track_render.render_tracks(source, result, tmp_path)

    assert not (tmp_path / "switches").exists()


def test_render_comparison_image_works_at_the_image_edge_and_for_small_frames(tmp_path):
    # Box am linken Rand und Bild kleiner als der Ausschnitt: darf nicht abstürzen
    source, result, candidate = _switch_case(size=(320, 200), x=2.0)

    track_render.render_tracks(source, result, tmp_path, (candidate,))

    assert (tmp_path / "switches" / "switch_001.png").exists()
