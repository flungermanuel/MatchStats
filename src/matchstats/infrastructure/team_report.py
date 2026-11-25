"""Schreibt die Teammessung als team_report.json (Maschine) und team_report.md (zum Lesen)."""

import dataclasses
import json
import platform
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path

from matchstats.application.team_evaluation import TeamEvaluationRun
from matchstats.domain.settings import Settings
from matchstats.domain.teams import UNKNOWN, Table, accuracy, accuracy_per_class, unknown_count
from matchstats.domain.testset import CLASSES

SCHEMA_VERSION = 1


def _pct(value: float | None) -> str:
    return "–" if value is None else f"{value * 100:.1f} %"


def _numpy_version() -> str | None:
    try:
        return version("numpy")
    except PackageNotFoundError:
        return None


def _parameters(settings: Settings) -> dict[str, object]:
    return {
        f.name: getattr(settings, f.name)
        for f in dataclasses.fields(settings)
        if f.name.startswith("team_")
    }


def _table_lines(title: str, table: Table) -> list[str]:
    columns = (*CLASSES, UNKNOWN)
    lines = [f"### {title}", "", "| Wahr \\ Vorhergesagt | " + " | ".join(columns) + " |"]
    lines.append("|---|" + "---|" * len(columns))
    for truth in CLASSES:
        lines.append(f"| {truth} | " + " | ".join(str(table[truth][c]) for c in columns) + " |")
    return [*lines, ""]


def write_team_report(run: TeamEvaluationRun, out_dir: Path, settings: Settings) -> None:
    """Fehlende Werte (z. B. keine ferne Box) bleiben null bzw. "–", nie 0."""
    out_dir.mkdir(parents=True, exist_ok=True)
    tables = {"total": run.confusion, "near": run.confusion_near, "far": run.confusion_far}
    acc = {
        "total": accuracy(run.confusion),
        "per_class": accuracy_per_class(run.confusion),
        "near": accuracy(run.confusion_near),
        "far": accuracy(run.confusion_far),
    }
    payload = {
        "schema_version": SCHEMA_VERSION,
        "versions": {"python": platform.python_version(), "numpy": _numpy_version()},
        "near_far_height_px": run.near_far_height,
        "parameters": _parameters(settings),
        "clip_mappings": run.clip_mappings,
        "clip_groups": run.clip_groups,
        "accuracy": acc,
        "unknown": unknown_count(run.confusion),
        "confusion": tables,
    }
    (out_dir / "team_report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        "# Teamzuordnung",
        "",
        f"Nah/fern-Grenze: Boxhöhe {run.near_far_height} px (Median). Nah = Höhe >= Grenze.",
        "Je Clip wird die bessere A/B-Zuordnung gewählt (Farbgruppen gelten nur je Clip).",
        "",
        f"Trefferquote gesamt: {_pct(acc['total'])}, nah: {_pct(acc['near'])}, "
        f"fern: {_pct(acc['far'])}; unbekannt: {payload['unknown']} Boxen (zählt als falsch).",
        "",
        "Trefferquote je Klasse: "
        + ", ".join(f"{c} {_pct(v)}" for c, v in acc["per_class"].items()),
        "",
        *_table_lines("Verwechslungstabelle gesamt", run.confusion),
        *_table_lines("nah", run.confusion_near),
        *_table_lines("fern", run.confusion_far),
        "Farbgruppen je Clip (Boxen je Gruppe, absteigend):",
        "",
        *[
            f"- {clip}: {', '.join(str(s) for s in sizes)} ({len(sizes)} Gruppen)"
            for clip, sizes in run.clip_groups.items()
        ],
        "",
        "Hinweis: Die A/B- und Torwart/Schiedsrichter-Zuordnung wird je Clip anhand der "
        "Wahrheit gewählt (Orakel); die Trefferquote ist daher optimistisch.",
        "",
        "Overlay-Bilder: zuerst Bilder mit Fehlern (rot, unbekannt zählt als Fehler), "
        "danach gleichmäßig verteilte ohne Fehler.",
    ]
    (out_dir / "team_report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
