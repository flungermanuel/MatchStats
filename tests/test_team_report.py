"""T5a (b): Bericht (JSON, Markdown) und Overlay-Bild der Teamzuordnung."""

import json

import numpy as np
from PIL import Image

from matchstats.application.team_evaluation import TeamEvaluationRun
from matchstats.domain.settings import Settings
from matchstats.domain.teams import UNKNOWN, TeamPrediction, confusion_table
from matchstats.domain.testset import CLASSES, LabeledBox
from matchstats.infrastructure.image_io import save_team_overlay
from matchstats.infrastructure.team_report import write_team_report


def _run(truth, predicted, near_far=52.0, clip_groups=None) -> TeamEvaluationRun:
    table = confusion_table(truth, predicted)
    empty = confusion_table([], [])
    extra = {"clip_groups": clip_groups} if clip_groups is not None else {}
    return TeamEvaluationRun(
        near_far,
        table,
        table,  # "nah" = alles
        empty,  # "fern" = leer: Quote fehlt
        {"clip1": {c: c for c in CLASSES}},
        {"clip1/a.png": [TeamPrediction(p, 0.9) for p in predicted]},
        **extra,
    )


def _read(tmp_path):
    return json.loads((tmp_path / "team_report.json").read_text(encoding="utf-8"))


def _typical_run():
    truth = ["team_a", "team_a", "team_b", "goalkeeper"]
    predicted = ["team_a", "team_b", "team_b", None]
    return _run(truth, predicted)


def test_report_json_has_schema_version_border_and_group_mapping(tmp_path):
    write_team_report(_typical_run(), tmp_path, Settings())

    data = _read(tmp_path)

    assert data["schema_version"] == 1
    assert data["near_far_height_px"] == 52.0
    assert data["clip_mappings"]["clip1"]["team_a"] == "team_a"


def test_report_json_has_accuracy_total_per_class_near_and_far(tmp_path):
    write_team_report(_typical_run(), tmp_path, Settings())

    accuracy = _read(tmp_path)["accuracy"]

    assert accuracy["total"] == 0.5
    assert accuracy["per_class"]["team_a"] == 0.5
    assert accuracy["per_class"]["team_b"] == 1.0
    assert accuracy["per_class"]["goalkeeper"] == 0.0
    assert accuracy["near"] == 0.5


def test_report_json_stores_missing_values_as_null_not_zero(tmp_path):
    write_team_report(_typical_run(), tmp_path, Settings())

    accuracy = _read(tmp_path)["accuracy"]

    assert accuracy["far"] is None  # keine fernen Boxen
    assert accuracy["per_class"]["referee"] is None  # kein Schiedsrichter beschriftet


def test_report_json_counts_unknown_and_has_confusion_table_with_unknown_column(tmp_path):
    write_team_report(_typical_run(), tmp_path, Settings())

    data = _read(tmp_path)

    assert data["unknown"] == 1
    assert data["confusion"]["total"]["goalkeeper"][UNKNOWN] == 1
    assert data["confusion"]["total"]["team_a"]["team_b"] == 1
    assert set(data["confusion"]) == {"total", "near", "far"}


def test_report_json_snapshots_all_team_parameters(tmp_path):
    settings = Settings(team_cluster_count=4, team_upper_body_fraction=0.4)
    write_team_report(_typical_run(), tmp_path, settings)

    parameters = _read(tmp_path)["parameters"]

    assert parameters["team_cluster_count"] == 4
    assert parameters["team_upper_body_fraction"] == 0.4
    assert "team_min_pixels" in parameters
    assert "team_grass_hue_range" in parameters
    assert all(name.startswith("team_") for name in parameters)


def test_report_markdown_has_confusion_table_with_truth_rows_and_unknown_column(tmp_path):
    write_team_report(_typical_run(), tmp_path, Settings())

    lines = (tmp_path / "team_report.md").read_text(encoding="utf-8").splitlines()

    header = next(line for line in lines if UNKNOWN in line and line.startswith("|"))
    for column in CLASSES:
        assert column in header
    for truth in CLASSES:
        assert any(line.startswith(f"| {truth} ") for line in lines)


def test_report_markdown_shows_dash_for_missing_values_and_names_overlay_criterion(tmp_path):
    write_team_report(_typical_run(), tmp_path, Settings())

    text = (tmp_path / "team_report.md").read_text(encoding="utf-8")

    assert "–" in text
    assert "Overlay" in text and "Fehler" in text  # Auswahlkriterium der Beispielbilder


def test_report_without_any_boxes_writes_nulls(tmp_path):
    empty = confusion_table([], [])
    run = TeamEvaluationRun(None, empty, empty, empty, {}, {})

    write_team_report(run, tmp_path, Settings())

    data = _read(tmp_path)
    assert data["near_far_height_px"] is None
    assert data["accuracy"]["total"] is None


def test_report_json_has_group_sizes_per_clip(tmp_path):
    run = _run(["team_a"], ["team_a"], clip_groups={"clip1": [8, 3, 1], "clip2": [5]})

    write_team_report(run, tmp_path, Settings())

    assert _read(tmp_path)["clip_groups"] == {"clip1": [8, 3, 1], "clip2": [5]}


def test_report_markdown_shows_number_and_sizes_of_color_groups_per_clip(tmp_path):
    run = _run(["team_a"], ["team_a"], clip_groups={"clip1": [8, 3, 1]})

    write_team_report(run, tmp_path, Settings())

    text = (tmp_path / "team_report.md").read_text(encoding="utf-8")
    line = next(line for line in text.splitlines() if "clip1" in line and "8, 3, 1" in line)
    assert "3" in line  # Anzahl der Gruppen


def test_team_evaluation_run_clip_groups_defaults_to_empty_dict():
    empty = confusion_table([], [])

    run = TeamEvaluationRun(None, empty, empty, empty, {}, {})

    assert run.clip_groups == {}


# --- Overlay ---


def _overlay(tmp_path, label, predicted):
    image = np.zeros((100, 100, 3), dtype=np.uint8)
    box = LabeledBox(10, 10, 40, 60, label)
    target = tmp_path / "o" / "clip1" / "a.png"
    save_team_overlay(image, [box], [TeamPrediction(predicted, 0.9)], target)
    return target, np.array(Image.open(target).convert("RGB"))


def test_overlay_file_is_created_including_missing_folders(tmp_path):
    target, _ = _overlay(tmp_path, "team_a", "team_a")

    assert target.is_file()
    assert Image.open(target).size == (100, 100)


def test_overlay_draws_wrong_predictions_red_and_correct_ones_not_red(tmp_path):
    _, wrong = _overlay(tmp_path, "team_a", "team_b")
    _, right = _overlay(tmp_path, "team_a", "team_a")

    r, g, b = (int(v) for v in wrong[40, 10])  # linke Boxkante
    assert r > 200 and g < 100 and b < 100
    r, g, b = (int(v) for v in right[40, 10])
    assert not (r > 200 and g < 100 and b < 100)
    assert (right[40, 10] != 0).any()  # überhaupt gezeichnet


def test_overlay_uses_different_colors_for_team_a_and_team_b(tmp_path):
    _, a = _overlay(tmp_path, "team_a", "team_a")
    _, b = _overlay(tmp_path, "team_b", "team_b")

    assert tuple(a[40, 10]) != tuple(b[40, 10])


def test_overlay_marks_unknown_prediction_as_error(tmp_path):
    _, unknown = _overlay(tmp_path, "team_a", None)

    r, g, b = (int(v) for v in unknown[40, 10])
    assert r > 200 and g < 100 and b < 100
