"""Abnahmetest T1: `matchstats run clip.mp4 --out ergebnis/` erzeugt ein leeres Ergebnis."""

import json
import subprocess
import sys

from conftest import requires_ffmpeg
from matchstats.cli import main


def _fake_clip(tmp_path):
    # In T1 wird das Video nicht gelesen; eine kleine Dummy-Datei genügt.
    clip = tmp_path / "clip.mp4"
    clip.write_bytes(b"dummy")
    return clip


def test_run_creates_empty_valid_result(tmp_path):
    out = tmp_path / "ergebnis"
    code = main(["run", str(_fake_clip(tmp_path)), "--out", str(out)])

    assert code == 0
    result = json.loads((out / "tracks.json").read_text(encoding="utf-8"))
    assert result["schema_version"] == 1
    assert result["source"] == "clip.mp4"  # nur der Dateiname, kein Pfad
    assert result["tracks"] == []
    assert result["config"]["detect_every"] == 5


def test_run_fails_for_missing_clip(tmp_path):
    code = main(["run", str(tmp_path / "gibt_es_nicht.mp4"), "--out", str(tmp_path / "out")])

    assert code != 0
    assert not (tmp_path / "out" / "tracks.json").exists()


@requires_ffmpeg
def test_sample_frames_command_writes_frames_and_manifest(make_clip, tmp_path, capsys):
    out = tmp_path / "frames"
    code = main(["sample-frames", str(make_clip("clip1.mp4")), "--out", str(out), "--count", "3"])

    assert code == 0
    assert len(list(out.glob("clip1_f*.png"))) == 3
    assert len(json.loads((out / "manifest.json").read_text(encoding="utf-8"))) == 3
    assert capsys.readouterr().out.strip() != ""


@requires_ffmpeg
def test_sample_frames_command_uses_frames_per_clip_from_settings_by_default(make_clip, tmp_path):
    out = tmp_path / "frames"
    code = main(["sample-frames", str(make_clip("clip1.mp4")), "--out", str(out)])

    assert code == 0
    assert len(list(out.glob("clip1_f*.png"))) == 20


@requires_ffmpeg
def test_sample_frames_command_accepts_several_clips(make_clip, tmp_path):
    out = tmp_path / "frames"
    clips = [str(make_clip("clip1.mp4")), str(make_clip("clip2.mp4"))]
    code = main(["sample-frames", *clips, "--out", str(out), "--count", "2"])

    assert code == 0
    assert len(list(out.glob("clip1_f*.png"))) == 2
    assert len(list(out.glob("clip2_f*.png"))) == 2


def test_sample_frames_command_fails_with_exit_2_for_missing_clip(tmp_path, capsys):
    code = main(
        ["sample-frames", str(tmp_path / "gibt_es_nicht.mp4"), "--out", str(tmp_path / "f")]
    )

    assert code == 2
    assert capsys.readouterr().err.strip() != ""


def test_module_entry_point_works(tmp_path):
    out = tmp_path / "ergebnis"
    proc = subprocess.run(
        [sys.executable, "-m", "matchstats", "run", str(_fake_clip(tmp_path)), "--out", str(out)],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert (out / "tracks.json").exists()


def test_evaluate_reports_missing_testset_with_exit_code_2(tmp_path):
    code = main(
        ["evaluate", "--testset", str(tmp_path / "fehlt.json"), "--out", str(tmp_path / "out")]
    )

    assert code == 2
