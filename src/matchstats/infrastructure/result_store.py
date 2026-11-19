"""Speichert und lädt das Ergebnis eines Laufs (jede Stufe sichert ihr Zwischenergebnis)."""

import json
from dataclasses import asdict
from pathlib import Path

from matchstats.domain.result import SCHEMA_VERSION, RunResult
from matchstats.domain.tracking import Track, TrackPoint
from matchstats.infrastructure.json_io import write_json_atomic

TRACKS_FILE = "tracks.json"


def save_result(result: RunResult, out_dir: Path) -> Path:
    target = out_dir / TRACKS_FILE
    data = asdict(result)
    data["config"] = data.pop("settings")
    write_json_atomic(target, data)
    return target


def load_result(path: Path) -> RunResult:
    """Lädt tracks.json (nur Version 2; ältere Dateien werden mit Meldung abgelehnt)."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    version = data.get("schema_version")
    if version != SCHEMA_VERSION:
        raise ValueError(
            f"{Path(path).name}: schema_version {version!r} wird nicht unterstützt, "
            f"erwartet {SCHEMA_VERSION}"
        )
    tracks = tuple(
        Track(id=t["id"], points=tuple(TrackPoint(**p) for p in t["points"]))
        for t in data["tracks"]
    )
    return RunResult(
        source=data["source"],
        settings=data["config"],
        tracks=tracks,
        fps=data["fps"],
        frame_count=data["frame_count"],
        versions=data["versions"],
        schema_version=version,
    )
