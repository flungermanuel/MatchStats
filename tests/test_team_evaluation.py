"""T5a (b): Messung der Teamzuordnung je Clip (rein, mit Fake-Klassifikator, ohne Dateien)."""

import numpy as np

from matchstats.application.team_evaluation import (
    TeamEvaluationRun,
    evaluate_teams,
    select_overlay_keys,
)
from matchstats.domain.teams import UNKNOWN, TeamPrediction, accuracy, accuracy_per_class
from matchstats.domain.testset import LabeledBox, LabeledImage


def _image(key: str, labels: list[str], height: float = 60) -> LabeledImage:
    boxes = tuple(LabeledBox(10 + 40 * n, 10, 20, height, label) for n, label in enumerate(labels))
    return LabeledImage(key, 320, 180, boxes)


class PositionClassifier:
    """Sagt je nach Box-x voraus (x = 10 + 40 * n); `answers` je Clip-Aufruf auswechselbar.

    Merkt sich, wie viele Bilder/Boxen je Aufruf kamen: ein Aufruf = ein Clip.
    """

    def __init__(self, answers: list[dict[float, str | None]]):
        self.answers = answers  # eine Zuordnung x -> Klasse je Aufruf, in Aufrufreihenfolge
        self.calls: list[int] = []

    def classify(self, images, boxes):
        answer = self.answers[len(self.calls)]
        self.calls.append(len(boxes))
        assert len(images) == len(boxes)
        return [
            TeamPrediction(None, None) if answer[b.x] is None else TeamPrediction(answer[b.x], 0.9)
            for b in boxes
        ]


def _load(_key: str) -> np.ndarray:
    return np.zeros((180, 320, 3), dtype=np.uint8)


TRUTH = ["team_a", "team_b", "goalkeeper"]
AS_TRUTH = {10: "team_a", 50: "team_b", 90: "goalkeeper"}
SWAPPED = {10: "team_b", 50: "team_a", 90: "goalkeeper"}


def _two_clips() -> list[LabeledImage]:
    return [_image("clip1/a.png", TRUTH), _image("clip2/a.png", TRUTH)]


def test_swapped_team_labels_in_one_clip_still_count_as_correct():
    classifier = PositionClassifier([SWAPPED, AS_TRUTH])  # Clip 1 vertauscht, Clip 2 nicht

    run = evaluate_teams(classifier, _two_clips(), _load)

    assert isinstance(run, TeamEvaluationRun)
    assert accuracy(run.confusion) == 1.0
    assert all(v == 1.0 for v in accuracy_per_class(run.confusion).values() if v is not None)


def test_best_group_mapping_per_clip_is_part_of_the_result():
    classifier = PositionClassifier([SWAPPED, AS_TRUTH])

    run = evaluate_teams(classifier, _two_clips(), _load)

    assert run.clip_mappings["clip1"]["team_a"] == "team_b"
    assert run.clip_mappings["clip1"]["team_b"] == "team_a"
    assert run.clip_mappings["clip2"]["team_a"] == "team_a"
    assert run.clip_mappings["clip1"]["goalkeeper"] == "goalkeeper"
    assert set(run.clip_mappings) == {"clip1", "clip2"}


def test_each_clip_is_classified_in_its_own_call():
    classifier = PositionClassifier([AS_TRUTH, AS_TRUTH])

    evaluate_teams(classifier, _two_clips(), _load)

    assert classifier.calls == [3, 3]  # nie beide Clips zusammen


def test_predictions_per_image_are_listed_after_mapping_in_box_order():
    classifier = PositionClassifier([SWAPPED, AS_TRUTH])

    run = evaluate_teams(classifier, _two_clips(), _load)

    assert [p.label for p in run.predictions["clip1/a.png"]] == TRUTH  # schon zurückgetauscht
    assert [p.label for p in run.predictions["clip2/a.png"]] == TRUTH


def test_unknown_predictions_are_not_correct_and_counted_separately():
    answer = {10: "team_a", 50: None, 90: "goalkeeper"}
    classifier = PositionClassifier([answer])

    run = evaluate_teams(classifier, [_image("clip1/a.png", TRUTH)], _load)

    assert run.confusion["team_b"][UNKNOWN] == 1
    assert accuracy(run.confusion) == 2 / 3
    assert run.predictions["clip1/a.png"][1].label is None


def test_near_far_tables_use_median_box_height_as_border():
    images = [_image("clip1/a.png", ["team_a"], 20), _image("clip1/b.png", ["team_a"], 100)]
    classifier = PositionClassifier([{10: "team_a"}])

    run = evaluate_teams(classifier, images, _load)

    assert run.near_far_height == 60.0
    assert sum(sum(row.values()) for row in run.confusion_near.values()) == 1
    assert sum(sum(row.values()) for row in run.confusion_far.values()) == 1
    assert sum(sum(row.values()) for row in run.confusion.values()) == 2


class SizedClassifier(PositionClassifier):
    """Wie PositionClassifier, plus Gruppengrößen (nur der Farbklassifikator hat das)."""

    def last_group_sizes(self) -> list[int]:
        return [len(self.calls) + 4, 2]  # je Aufruf (= Clip) andere Größen


def test_clip_groups_collects_group_sizes_per_clip_from_optional_method():
    classifier = SizedClassifier([AS_TRUTH, AS_TRUTH])

    run = evaluate_teams(classifier, _two_clips(), _load)

    assert run.clip_groups == {"clip1": [5, 2], "clip2": [6, 2]}


def test_clip_groups_is_empty_list_for_classifier_without_the_method():
    classifier = PositionClassifier([AS_TRUTH, AS_TRUTH])

    run = evaluate_teams(classifier, _two_clips(), _load)

    assert run.clip_groups == {"clip1": [], "clip2": []}


# --- Auswahl der Overlay-Bilder ---


def _run_with_errors(
    error_keys: set[str], keys: list[str]
) -> tuple[list[LabeledImage], TeamEvaluationRun]:
    images = [_image(k, ["team_a"]) for k in keys]
    predictions = {
        k: [TeamPrediction("team_b" if k in error_keys else "team_a", 0.9)] for k in keys
    }
    empty: dict = {}
    return images, TeamEvaluationRun(60.0, empty, empty, empty, {}, predictions)


def test_overlay_selection_takes_images_with_errors_first_and_fills_up_to_count():
    keys = [f"clip1/{i}.png" for i in range(8)]
    errors = {"clip1/5.png", "clip1/6.png", "clip1/7.png"}
    images, run = _run_with_errors(errors, keys)

    chosen = select_overlay_keys(images, run, 4)

    assert len(chosen) == 4
    assert errors <= set(chosen)


def test_overlay_selection_with_more_errors_than_count_shows_only_errors():
    keys = [f"clip1/{i}.png" for i in range(6)]
    errors = {"clip1/2.png", "clip1/3.png", "clip1/4.png"}
    images, run = _run_with_errors(errors, keys)

    chosen = select_overlay_keys(images, run, 2)

    assert len(chosen) == 2
    assert set(chosen) <= errors


def test_overlay_selection_without_errors_still_returns_count_images():
    keys = [f"clip1/{i}.png" for i in range(5)]
    images, run = _run_with_errors(set(), keys)

    assert len(select_overlay_keys(images, run, 3)) == 3


def test_overlay_selection_with_fewer_images_than_count_returns_all_without_duplicates():
    keys = ["clip1/0.png", "clip1/1.png"]
    images, run = _run_with_errors({"clip1/1.png"}, keys)

    chosen = select_overlay_keys(images, run, 6)

    assert sorted(chosen) == keys


def test_unknown_prediction_counts_as_error_for_overlay_selection():
    images = [_image("clip1/0.png", ["team_a"]), _image("clip1/1.png", ["team_a"])]
    predictions = {
        "clip1/0.png": [TeamPrediction("team_a", 0.9)],
        "clip1/1.png": [TeamPrediction(None, None)],
    }
    empty: dict = {}
    run = TeamEvaluationRun(60.0, empty, empty, empty, {}, predictions)

    assert select_overlay_keys(images, run, 1) == ["clip1/1.png"]
