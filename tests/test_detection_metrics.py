"""Messregeln aus der Spezifikation: Treffer ab IoU 0,5, jede Beschriftung nur einmal."""

import pytest

from matchstats.domain.detection import Detection, iou, non_max_suppression
from matchstats.domain.metrics import evaluate_image, median_height, summarize
from matchstats.domain.testset import LabeledBox


def box(x, y, w, h):
    return LabeledBox(x, y, w, h, "team_a")


def det(x, y, w, h, score=0.9):
    return Detection(x, y, w, h, score)


def test_iou_of_identical_boxes_is_one():
    assert iou(det(0, 0, 10, 10), box(0, 0, 10, 10)) == pytest.approx(1.0)


def test_iou_of_disjoint_boxes_is_zero():
    assert iou(det(0, 0, 10, 10), box(20, 20, 10, 10)) == 0.0


def test_iou_of_half_overlapping_boxes_is_one_third():
    # Überlappung 5x10 = 50, Vereinigung 150
    assert iou(det(0, 0, 10, 10), box(5, 0, 10, 10)) == pytest.approx(1 / 3)


def test_hit_requires_iou_of_at_least_half():
    labels = [box(0, 0, 10, 10)]
    # IoU genau 0,5: Box 10x10 gegen Box 10x5 -> 50/100
    assert evaluate_image([det(0, 0, 10, 5)], labels, near_far_height=1).true_positives == 1
    # IoU knapp darunter
    assert evaluate_image([det(0, 0, 10, 4.9)], labels, near_far_height=1).true_positives == 0


def test_each_label_can_only_be_hit_once():
    labels = [box(0, 0, 10, 10)]
    result = evaluate_image([det(0, 0, 10, 10, 0.9), det(0, 0, 10, 10, 0.8)], labels, 1)

    assert result.true_positives == 1
    assert result.detections == 2  # die zweite Erkennung ist ein Fehlalarm


def test_detection_with_higher_score_gets_the_label_first():
    labels = [box(0, 0, 10, 10)]
    result = evaluate_image([det(1, 0, 10, 10, 0.5), det(0, 0, 10, 10, 0.9)], labels, 1)

    assert result.true_positives == 1


def test_recall_and_precision_are_computed_from_all_images():
    labels = [box(0, 0, 10, 10), box(100, 0, 10, 10)]
    first = evaluate_image([det(0, 0, 10, 10), det(500, 500, 10, 10)], labels, 1)
    second = evaluate_image([], [box(0, 0, 10, 10)], 1)

    summary = summarize([first, second])

    # 3 Beschriftungen, 1 Treffer, 2 Erkennungen
    assert summary.recall == pytest.approx(1 / 3)
    assert summary.precision == pytest.approx(1 / 2)


def test_precision_is_missing_when_nothing_was_detected():
    summary = summarize([evaluate_image([], [box(0, 0, 10, 10)], 1)])

    assert summary.precision is None  # unbekannt ist nicht null
    assert summary.recall == 0.0


def test_recall_is_reported_separately_for_near_and_far_boxes():
    near = box(0, 0, 20, 100)  # Höhe 100 >= Grenze -> nah
    far = box(200, 0, 5, 30)  # Höhe 30 < Grenze -> fern
    result = evaluate_image([det(0, 0, 20, 100)], [near, far], near_far_height=50)

    summary = summarize([result])

    assert summary.recall_near == 1.0
    assert summary.recall_far == 0.0
    assert summary.labels_near == 1
    assert summary.labels_far == 1


def test_median_height_of_labels_is_used_as_near_far_border():
    images = [[box(0, 0, 1, 10), box(0, 0, 1, 20)], [box(0, 0, 1, 40)]]

    assert median_height(images) == 20


def test_nms_removes_overlapping_duplicate_with_lower_score():
    kept = non_max_suppression([det(0, 0, 10, 10, 0.6), det(1, 0, 10, 10, 0.9)], iou_threshold=0.5)

    assert [d.score for d in kept] == [0.9]


def test_nms_keeps_separate_boxes():
    kept = non_max_suppression([det(0, 0, 10, 10), det(50, 0, 10, 10)], iou_threshold=0.5)

    assert len(kept) == 2
