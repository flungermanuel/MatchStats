"""Abnahmetest T3b AK 3: Nach der Migration liefert `evaluate --game spiel-001 --half 1` dieselben
Zahlen wie die T3-Messung (data/ergebnis/t3/report.json). Laufzeiten sind ausgenommen.

Die Daten liegen lokal (nicht im Git). Fehlen sie, wird übersprungen. Der Test lässt die echten
Detektoren über 60 Bilder laufen (viele Minuten auf der CPU); er läuft deshalb nur, wenn die
Umgebungsvariable MATCHSTATS_SLOW=1 gesetzt ist.
"""

import json
import os
from pathlib import Path

import pytest

from matchstats.cli import main

ROOT = Path(__file__).resolve().parents[1]
LIBRARY = ROOT / "data" / "library"
BASELINE = ROOT / "data" / "ergebnis" / "t3" / "report.json"

pytestmark = [
    pytest.mark.skipif(
        not (LIBRARY / "spiel-001").is_dir() or not BASELINE.is_file(),
        reason="data/library/spiel-001 oder data/ergebnis/t3/report.json fehlt (lokal)",
    ),
    pytest.mark.skipif(
        os.environ.get("MATCHSTATS_SLOW") != "1",
        reason="langsam (echte Detektoren); mit MATCHSTATS_SLOW=1 einschalten",
    ),
]

COMPARED = ("images", "labels", "labels_near", "labels_far", "detections", "true_positives")
RATIOS = ("recall", "precision", "recall_near", "recall_far")


def test_migrated_game_gives_same_recall_and_precision_as_the_t3_baseline(tmp_path):
    out = tmp_path / "bericht"
    code = main([
        "evaluate", "--game", "spiel-001", "--half", "1", "--out", str(out),
        "--library", str(LIBRARY),
    ])  # fmt: skip
    assert code == 0

    new = json.loads((out / "report.json").read_text(encoding="utf-8"))
    old = json.loads(BASELINE.read_text(encoding="utf-8"))
    assert new["near_far_height_px"] == old["near_far_height_px"]
    new_by_name = {v["name"]: v for v in new["variants"]}
    old_by_name = {v["name"]: v for v in old["variants"]}
    assert new_by_name.keys() == old_by_name.keys()
    for name, expected in old_by_name.items():
        for key in COMPARED + RATIOS:  # seconds_per_image bewusst nicht
            assert new_by_name[name][key] == pytest.approx(expected[key]), f"{name}: {key}"
