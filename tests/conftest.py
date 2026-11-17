"""Gemeinsame Hilfen: kleines synthetisches Video (kein echtes Material, keine Personen)."""

import shutil
import subprocess
from pathlib import Path

import pytest

requires_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="ffmpeg/ffprobe nicht installiert",
)


@pytest.fixture
def make_clip(tmp_path):
    """Erzeugt ein 4-Sekunden-Testvideo (320x180, 25 fps) mit dem angegebenen Namen."""

    def _make(name: str = "clip1.mp4", duration: int = 4) -> Path:
        clip = tmp_path / name
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "lavfi", "-i", f"testsrc=duration={duration}:size=320x180:rate=25",
                "-pix_fmt", "yuv420p", "-c:v", "libx264", str(clip),
            ],
            check=True,
        )  # fmt: skip
        return clip

    return _make
