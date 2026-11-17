"""T2: Bilder werden gleichmäßig aus dem Clip gezogen (synthetisches Video, schnell)."""

import json
import re
import subprocess

import pytest

from conftest import requires_ffmpeg
from matchstats.infrastructure import frame_sampler
from matchstats.infrastructure.frame_sampler import sample_frames

pytestmark = requires_ffmpeg

NAME_PATTERN = re.compile(r"clip\d+_f\d{5}\.png")


def test_sampler_writes_requested_number_of_pngs(make_clip, tmp_path):
    out = tmp_path / "frames"
    frames = sample_frames(make_clip("clip1.mp4"), out, 5)

    assert len(frames) == 5
    assert len(list(out.glob("*.png"))) == 5


def test_sampler_names_files_by_clip_and_five_digit_frame_number(make_clip, tmp_path):
    out = tmp_path / "frames"
    frames = sample_frames(make_clip("clip1.mp4"), out, 5)

    for f in frames:
        assert NAME_PATTERN.fullmatch(f.file_name)
        assert f.file_name == f"clip1_f{f.frame_number:05d}.png"
        assert (out / f.file_name).is_file()


def test_sampler_picks_section_midpoints_of_the_clip(make_clip, tmp_path):
    # 4 s bei 25 fps, 5 Abschnitte: Mitten 0.4/1.2/2.0/2.8/3.6 s -> Bild 10/30/50/70/90
    frames = sample_frames(make_clip("clip1.mp4"), tmp_path / "frames", 5)

    assert [f.time_s for f in frames] == pytest.approx([0.4, 1.2, 2.0, 2.8, 3.6], abs=0.05)
    assert [f.frame_number for f in frames] == [10, 30, 50, 70, 90]
    assert all(f.clip == "clip1.mp4" for f in frames)


def test_sampler_writes_manifest_matching_the_frames(make_clip, tmp_path):
    out = tmp_path / "frames"
    frames = sample_frames(make_clip("clip1.mp4"), out, 5)

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert len(manifest) == 5
    for entry, frame in zip(manifest, frames, strict=True):
        assert set(entry) == {"clip", "time_s", "frame_number", "file_name"}
        assert entry["clip"] == "clip1.mp4"
        assert entry["frame_number"] == frame.frame_number
        assert entry["file_name"] == frame.file_name
        assert entry["time_s"] == pytest.approx(frame.time_s)


def test_sampler_adds_second_clip_to_manifest_instead_of_overwriting(make_clip, tmp_path):
    out = tmp_path / "frames"
    sample_frames(make_clip("clip1.mp4"), out, 3)
    sample_frames(make_clip("clip2.mp4"), out, 4)

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    clips = [e["clip"] for e in manifest]
    assert clips.count("clip1.mp4") == 3
    assert clips.count("clip2.mp4") == 4
    assert len(list(out.glob("clip1_f*.png"))) == 3
    assert len(list(out.glob("clip2_f*.png"))) == 4


def test_sampler_replaces_entries_of_same_clip_when_run_again(make_clip, tmp_path):
    out = tmp_path / "frames"
    clip = make_clip("clip1.mp4")
    sample_frames(clip, out, 3)
    sample_frames(clip, out, 5)

    manifest = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
    assert [e["clip"] for e in manifest] == ["clip1.mp4"] * 5


def test_sampler_raises_for_missing_clip(tmp_path):
    with pytest.raises(FileNotFoundError):
        sample_frames(tmp_path / "gibt_es_nicht.mp4", tmp_path / "frames", 5)


def _make_audio_only(path):
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "sine=duration=2", str(path),
        ],
        check=True,
    )  # fmt: skip
    return path


def _fail_ffmpeg(monkeypatch):
    """Lässt nur ffmpeg-Aufrufe scheitern; ffprobe läuft normal weiter."""
    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if cmd[0] == "ffmpeg":
            raise subprocess.CalledProcessError(1, cmd)
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(frame_sampler.subprocess, "run", fake_run)


def _snapshot(out):
    return {p.name: p.read_bytes() for p in out.iterdir()}


def test_sampler_raises_sampling_error_for_file_without_video_stream(tmp_path):
    audio = _make_audio_only(tmp_path / "ton.wav")

    with pytest.raises(frame_sampler.FrameSamplingError):
        sample_frames(audio, tmp_path / "frames", 3)


def test_sampling_error_is_a_runtime_error():
    assert issubclass(frame_sampler.FrameSamplingError, RuntimeError)


def test_sampler_raises_sampling_error_when_ffmpeg_delivers_no_images(
    make_clip, tmp_path, monkeypatch
):
    clip = make_clip("clip1.mp4")  # vor dem Patchen erzeugen (die Fixture nutzt selbst ffmpeg)
    real_run = subprocess.run

    def silent_ffmpeg(cmd, *args, **kwargs):
        if cmd[0] == "ffmpeg":
            return subprocess.CompletedProcess(cmd, 0)  # Erfolg gemeldet, aber nichts geschrieben
        return real_run(cmd, *args, **kwargs)

    monkeypatch.setattr(frame_sampler.subprocess, "run", silent_ffmpeg)

    with pytest.raises(frame_sampler.FrameSamplingError):
        sample_frames(clip, tmp_path / "frames", 3)


def test_failed_rerun_keeps_old_pngs_and_manifest_unchanged(make_clip, tmp_path, monkeypatch):
    out = tmp_path / "frames"
    clip = make_clip("clip1.mp4")
    sample_frames(clip, out, 3)
    before = _snapshot(out)

    _fail_ffmpeg(monkeypatch)
    with pytest.raises(Exception):  # noqa: B017 - Art des Fehlers hier nicht entscheidend
        sample_frames(clip, out, 5)

    assert _snapshot(out) == before


def test_sampler_leaves_no_temp_files_after_success(make_clip, tmp_path):
    out = tmp_path / "frames"
    sample_frames(make_clip("clip1.mp4"), out, 4)

    assert [p.name for p in out.iterdir() if "_tmp" in p.name or p.suffix == ".tmp"] == []


def test_sampler_leaves_no_temp_files_after_failure(make_clip, tmp_path, monkeypatch):
    out = tmp_path / "frames"
    clip = make_clip("clip1.mp4")
    sample_frames(clip, out, 3)

    _fail_ffmpeg(monkeypatch)
    with pytest.raises(Exception):  # noqa: B017
        sample_frames(clip, out, 5)

    assert [p.name for p in out.iterdir() if "_tmp" in p.name or p.suffix == ".tmp"] == []
