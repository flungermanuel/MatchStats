"""T5a: Domäne der Teamzuordnung (rein): Verwechslungstabelle, beste A/B-Zuordnung, Trefferquote."""

import dataclasses

import pytest

from matchstats.domain.metrics import median_height
from matchstats.domain.teams import (
    UNKNOWN,
    TeamPrediction,
    accuracy,
    accuracy_per_class,
    best_team_mapping,
    confusion_near_far,
    confusion_table,
    unknown_count,
)
from matchstats.domain.testset import CLASSES, LabeledBox


def _table(truth, predicted):
    return confusion_table(truth=truth, predicted=predicted)


def test_team_prediction_holds_label_and_confidence_and_allows_unknown():
    known = TeamPrediction(label="team_a", confidence=0.9)
    unknown = TeamPrediction(label=None, confidence=None)

    assert known.label == "team_a" and known.confidence == 0.9
    assert unknown.label is None and unknown.confidence is None
    with pytest.raises(dataclasses.FrozenInstanceError):
        known.label = "team_b"  # type: ignore[misc]


def test_confusion_table_has_row_per_class_and_column_unknown():
    table = _table(["team_a"], ["team_a"])

    assert tuple(table.keys()) == CLASSES
    for row in table.values():
        assert tuple(row.keys()) == (*CLASSES, UNKNOWN)
    assert UNKNOWN == "unbekannt"


def test_confusion_table_counts_rows_as_truth_and_columns_as_prediction():
    table = _table(
        ["team_a", "team_a", "team_b", "referee"],
        ["team_a", "team_b", "team_b", "goalkeeper"],
    )

    assert table["team_a"]["team_a"] == 1
    assert table["team_a"]["team_b"] == 1
    assert table["team_b"]["team_b"] == 1
    assert table["referee"]["goalkeeper"] == 1
    assert sum(sum(row.values()) for row in table.values()) == 4


def test_confusion_table_counts_unknown_prediction_in_separate_column():
    table = _table(["team_a", "team_a"], ["team_a", None])

    assert table["team_a"][UNKNOWN] == 1
    assert table["team_a"]["team_a"] == 1
    assert unknown_count(table) == 1


def test_confusion_table_rejects_different_lengths():
    with pytest.raises(ValueError):
        _table(["team_a"], [])


def test_best_team_mapping_keeps_identity_when_teams_already_match():
    table = _table(["team_a"] * 3 + ["team_b"] * 3, ["team_a"] * 3 + ["team_b"] * 3)

    mapping = best_team_mapping(table)

    assert mapping["team_a"] == "team_a" and mapping["team_b"] == "team_b"


def test_best_team_mapping_swaps_teams_when_labels_are_exchanged():
    table = _table(["team_a"] * 3 + ["team_b"] * 3, ["team_b"] * 3 + ["team_a"] * 3)

    mapping = best_team_mapping(table)

    # Schlüssel = vorhergesagte Klasse, Wert = Klasse, als die sie gezählt wird.
    assert mapping["team_a"] == "team_b" and mapping["team_b"] == "team_a"


def test_best_team_mapping_never_changes_goalkeeper_and_referee():
    table = _table(
        ["team_a", "team_b", "goalkeeper", "referee"],
        ["team_b", "team_a", "goalkeeper", "referee"],
    )

    mapping = best_team_mapping(table)

    assert mapping["goalkeeper"] == "goalkeeper"
    assert mapping["referee"] == "referee"


def test_accuracy_counts_swapped_team_labels_as_correct_after_best_mapping():
    table = _table(["team_a"] * 4 + ["team_b"] * 4, ["team_b"] * 4 + ["team_a"] * 4)

    assert accuracy(table) == 1.0
    assert accuracy_per_class(table)["team_a"] == 1.0
    assert accuracy_per_class(table)["team_b"] == 1.0


def test_accuracy_counts_unknown_as_not_correct_and_in_denominator():
    table = _table(["team_a", "team_a", "team_b", "team_b"], ["team_a", None, "team_b", "team_b"])

    assert accuracy(table) == pytest.approx(0.75)
    assert accuracy_per_class(table)["team_a"] == pytest.approx(0.5)
    assert unknown_count(table) == 1


def test_accuracy_is_none_for_class_without_labels_not_zero():
    table = _table(["team_a", "team_b"], ["team_a", "team_b"])

    per_class = accuracy_per_class(table)

    assert per_class["goalkeeper"] is None
    assert per_class["referee"] is None
    assert per_class["team_a"] == 1.0


def test_accuracy_is_none_for_empty_table():
    assert accuracy(_table([], [])) is None


def test_accuracy_class_with_only_wrong_predictions_is_zero_not_none():
    table = _table(["goalkeeper", "team_a", "team_b"], ["team_a", "team_a", "team_b"])

    assert accuracy_per_class(table)["goalkeeper"] == 0.0


def test_near_far_split_uses_median_height_with_near_as_height_greater_or_equal():
    boxes = [LabeledBox(0, 0, 10, h, "team_a") for h in (20.0, 40.0, 60.0, 80.0)]
    limit = median_height([boxes])  # 50.0
    heights = [b.h for b in boxes]
    truth = ["team_a"] * 4
    predicted = ["team_a", "team_b", "team_a", None]

    near, far = confusion_near_far(heights, truth, predicted, limit)

    assert sum(sum(r.values()) for r in near.values()) == 2  # 60, 80
    assert sum(sum(r.values()) for r in far.values()) == 2  # 20, 40
    assert near["team_a"][UNKNOWN] == 1
    assert far["team_a"]["team_b"] == 1


def test_near_far_box_exactly_at_limit_counts_as_near():
    near, far = confusion_near_far([50.0], ["team_a"], ["team_a"], 50.0)

    assert near["team_a"]["team_a"] == 1
    assert sum(sum(r.values()) for r in far.values()) == 0


def test_best_team_mapping_swaps_goalkeeper_and_referee_when_that_gives_more_hits():
    table = _table(["goalkeeper"] * 3 + ["referee"] * 2, ["referee"] * 3 + ["goalkeeper"] * 2)

    mapping = best_team_mapping(table)

    assert mapping["goalkeeper"] == "referee" and mapping["referee"] == "goalkeeper"
    assert mapping["team_a"] == "team_a" and mapping["team_b"] == "team_b"


def test_best_team_mapping_keeps_goalkeeper_and_referee_on_tie():
    table = _table(["goalkeeper", "referee"], ["referee", "referee"])

    mapping = best_team_mapping(table)

    assert mapping == {c: c for c in CLASSES}


def test_best_team_mapping_swaps_teams_independently_of_goalkeeper_and_referee():
    table = _table(
        ["team_a"] * 3 + ["team_b"] * 3 + ["goalkeeper"] * 2 + ["referee"],
        ["team_b"] * 3 + ["team_a"] * 3 + ["goalkeeper"] * 2 + ["referee"],
    )

    mapping = best_team_mapping(table)

    assert mapping["team_a"] == "team_b" and mapping["team_b"] == "team_a"
    assert mapping["goalkeeper"] == "goalkeeper" and mapping["referee"] == "referee"


def test_best_team_mapping_can_swap_both_pairs_at_once():
    table = _table(
        ["team_a"] * 3 + ["team_b"] * 3 + ["goalkeeper"] * 2 + ["referee"] * 2,
        ["team_b"] * 3 + ["team_a"] * 3 + ["referee"] * 2 + ["goalkeeper"] * 2,
    )

    mapping = best_team_mapping(table)

    assert mapping == {
        "team_a": "team_b",
        "team_b": "team_a",
        "goalkeeper": "referee",
        "referee": "goalkeeper",
    }
