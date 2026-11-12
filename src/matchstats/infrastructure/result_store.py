"""Speichert das Ergebnis eines Laufs auf Platte (jede Stufe sichert ihr Zwischenergebnis)."""

import json
from dataclasses import asdict
from pathlib import Path

from matchstats.domain.result import RunResult

TRACKS_FILE = "tracks.json"


def save_result(result: RunResult, out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / TRACKS_FILE
    data = asdict(result)
    data["config"] = data.pop("settings")
    target.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
