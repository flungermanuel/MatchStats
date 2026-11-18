"""Schreibt die Messergebnisse als report.json (Maschine) und report.md (zum Lesen)."""

import json
from pathlib import Path

from matchstats.application.evaluation import EvaluationRun


def _pct(value: float | None) -> str:
    return "–" if value is None else f"{value * 100:.1f} %"


def write_report(runs: list[EvaluationRun], out_dir: Path) -> None:
    """Fehlende Werte (z. B. Precision ohne Erkennungen) bleiben null/"–", nie 0."""
    out_dir.mkdir(parents=True, exist_ok=True)
    border = runs[0].near_far_height if runs else None
    variants = [
        {
            "name": r.name,
            "images": r.summary.images,
            "labels": r.summary.labels,
            "labels_near": r.summary.labels_near,
            "labels_far": r.summary.labels_far,
            "detections": r.summary.detections,
            "true_positives": r.summary.true_positives,
            "recall": r.summary.recall,
            "precision": r.summary.precision,
            "recall_near": r.summary.recall_near,
            "recall_far": r.summary.recall_far,
            "seconds_per_image": r.seconds_per_image,
        }
        for r in runs
    ]
    payload = {"near_far_height_px": border, "variants": variants}
    (out_dir / "report.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    lines = [
        f"Nah/fern-Grenze: Boxhöhe {border} px (Median der Beschriftungen). Nah = Höhe >= Grenze.",
        "",
        "| Variante | Recall | Precision | Recall nah | Recall fern | Sekunden/Bild |",
        "|---|---|---|---|---|---|",
    ]
    for r in runs:
        s = r.summary
        lines.append(
            f"| {r.name} | {_pct(s.recall)} | {_pct(s.precision)} | {_pct(s.recall_near)} "
            f"| {_pct(s.recall_far)} | {r.seconds_per_image:.2f} |"
        )
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
