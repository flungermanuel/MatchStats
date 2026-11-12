"""Abnahmetest T1: `matchstats run clip.mp4 --out ergebnis/` erzeugt ein leeres Ergebnis."""

import json
import subprocess
import sys

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


def test_module_entry_point_works(tmp_path):
    out = tmp_path / "ergebnis"
    proc = subprocess.run(
        [sys.executable, "-m", "matchstats", "run", str(_fake_clip(tmp_path)), "--out", str(out)],
        capture_output=True,
        text=True,
    )

    assert proc.returncode == 0, proc.stderr
    assert (out / "tracks.json").exists()
