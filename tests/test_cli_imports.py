"""CLI: schwere Bibliotheken (cv2, scipy) werden erst im track-Befehl geladen."""

import subprocess
import sys


def test_importing_the_cli_does_not_load_cv2_or_scipy():
    code = (
        "import sys, matchstats.cli; "
        "bad = [m for m in ('cv2', 'scipy') if m in sys.modules]; "
        "sys.exit(1 if bad else 0)"
    )

    result = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)

    assert result.returncode == 0, result.stderr
