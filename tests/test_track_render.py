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
