"""Bericht: JSON und Markdown-Tabelle aus den Messläufen."""

import json

from matchstats.application.evaluation import EvaluationRun
from matchstats.domain.metrics import Summary
from matchstats.infrastructure.evaluation_report import write_report


def run(name: str, precision: float | None) -> EvaluationRun:
    summary = Summary(
        images=60,
        labels=100,
        detections=80,
        true_positives=50,
        labels_near=40,
        labels_far=60,
        recall=0.5,
        precision=precision,
        recall_near=0.9,
        recall_far=0.2,
    )
    return EvaluationRun(name, summary, 0.25, 52.0, {})


def test_report_json_contains_all_variants_with_time_and_split(tmp_path):
    write_report([run("rfdetr-whole", 0.625), run("rfdetr-tiles", 0.5)], tmp_path)

    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert [v["name"] for v in data["variants"]] == ["rfdetr-whole", "rfdetr-tiles"]
    first = data["variants"][0]
    assert first["recall_near"] == 0.9
    assert first["recall_far"] == 0.2
    assert first["seconds_per_image"] == 0.25
    assert data["near_far_height_px"] == 52.0


def test_report_stores_missing_precision_as_null_not_zero(tmp_path):
    write_report([run("leer", None)], tmp_path)

    data = json.loads((tmp_path / "report.json").read_text(encoding="utf-8"))

    assert data["variants"][0]["precision"] is None


def test_report_markdown_has_one_row_per_variant(tmp_path):
    write_report([run("a", 0.5), run("b", 0.5)], tmp_path)

    lines = (tmp_path / "report.md").read_text(encoding="utf-8").splitlines()

    assert sum(1 for line in lines if line.startswith("| a ") or line.startswith("| b ")) == 2
