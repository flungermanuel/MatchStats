"""OpenCvFrameSource: Bildauswahl, Farbreihenfolge, Verhalten bei abgebrochenem Dekodieren."""

import numpy as np
import pytest

cv2 = pytest.importorskip("cv2")

from matchstats.infrastructure.video_source import OpenCvFrameSource  # noqa: E402


def _write(path, frames=12, size=(64, 48), fps=25.0, color_bgr=(10, 20, 200)):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    for _ in range(frames):
        writer.write(np.full((size[1], size[0], 3), color_bgr, dtype=np.uint8))
    writer.release()
    return path


def test_frames_yield_indices_0_n_2n_and_so_on(tmp_path):
    source = OpenCvFrameSource(_write(tmp_path / "v.mp4", frames=12))

    indices = [i for i, _ in source.frames(5)]

    assert indices == [0, 5, 10]


def test_frames_are_delivered_in_rgb_order(tmp_path):
    source = OpenCvFrameSource(_write(tmp_path / "v.mp4", color_bgr=(10, 20, 200)))

    _, image = next(iter(source.frames(1)))

    r, g, b = image[24, 32]  # Mitte
    assert r > 150 and b < 60  # Blau-Rot nicht vertauscht (lossy Codec: Toleranz)
    assert image.shape == (48, 64, 3)


def test_frames_with_every_1_return_all_frames_of_a_complete_video(tmp_path):
    source = OpenCvFrameSource(_write(tmp_path / "v.mp4", frames=12))

    assert len(list(source.frames(1))) == source.frame_count == 12


def test_frames_raise_with_file_name_and_counts_when_decoding_stops_early(tmp_path):
    source = OpenCvFrameSource(_write(tmp_path / "v.mp4", frames=12))
    source.frame_count = 40  # Datei meldet mehr Bilder, als sich dekodieren lassen

    with pytest.raises(ValueError) as err:
        list(source.frames(1))

    message = str(err.value)
    assert "v.mp4" in message and "40" in message and "12" in message


def test_frames_tolerate_a_frame_count_that_is_off_by_two(tmp_path):
    source = OpenCvFrameSource(_write(tmp_path / "v.mp4", frames=12))
    source.frame_count = 14

    assert len(list(source.frames(1))) == 12


def test_frame_source_rejects_a_video_with_zero_fps(tmp_path, monkeypatch):
    path = _write(tmp_path / "v.mp4")
    monkeypatch.setattr("matchstats.infrastructure.video_source._read_fps", lambda capture: 0.0)

    with pytest.raises(ValueError, match="fps"):
        OpenCvFrameSource(path)


def test_frame_source_rejects_nan_fps(tmp_path, monkeypatch):
    path = _write(tmp_path / "v.mp4")
    monkeypatch.setattr(
        "matchstats.infrastructure.video_source._read_fps", lambda capture: float("nan")
    )

    with pytest.raises(ValueError, match="fps"):
        OpenCvFrameSource(path)
