"""Auswertungsstufe: Detektor auf beschrifteten Bildern messen (mit Fake-Detektor, ohne Modell)."""

import numpy as np

from matchstats.application.evaluation import evaluate_detector
from matchstats.domain.detection import Detection
from matchstats.domain.testset import LabeledBox, LabeledImage


def labeled(name, *boxes):
    return LabeledImage(name, 1920, 1080, tuple(LabeledBox(*b, "team_a") for b in boxes))


class PerfectDetector:
    """Gibt für jedes Bild genau die beschrifteten Boxen zurück (merkt sich per Bildinhalt)."""

    def __init__(self, truth: dict[int, list[Detection]]) -> None:
        self.truth = truth
        self.calls = 0

    def detect(self, image: np.ndarray) -> list[Detection]:
        self.calls += 1
        return self.truth[int(image[0, 0, 0])]


def fake_loader(index_by_name: dict[str, int]):
    def load(name: str) -> np.ndarray:
        image = np.zeros((4, 4, 3), dtype=np.uint8)
        image[0, 0, 0] = index_by_name[name]
        return image

    return load


def test_perfect_detector_gets_recall_and_precision_of_one():
    images = [labeled("a.png", (10, 10, 20, 80)), labeled("b.png", (50, 50, 10, 30))]
    truth = {
        0: [Detection(10, 10, 20, 80, 0.9)],
        1: [Detection(50, 50, 10, 30, 0.9)],
    }
    detector = PerfectDetector(truth)

    run = evaluate_detector(
        "perfekt", detector, images, fake_loader({"a.png": 0, "b.png": 1}), near_far_height=50
    )

    assert run.summary.recall == 1.0
    assert run.summary.precision == 1.0
    assert run.summary.recall_near == 1.0
    assert run.summary.recall_far == 1.0


def test_evaluation_warms_up_once_then_runs_detector_once_per_image():
    images = [labeled("a.png", (10, 10, 20, 80)), labeled("b.png", (50, 50, 10, 30))]
    detector = PerfectDetector({0: [], 1: []})

    run = evaluate_detector(
        "leer", detector, images, fake_loader({"a.png": 0, "b.png": 1}), near_far_height=50
    )

    assert detector.calls == 3  # 1 Aufwärmlauf (nicht gezählt) + 2 Bilder
    assert run.seconds_per_image >= 0
    assert run.summary.recall == 0.0
    assert run.summary.precision is None


def test_evaluation_keeps_detections_per_image_for_drawing():
    images = [labeled("a.png", (10, 10, 20, 80))]
    detector = PerfectDetector({0: [Detection(10, 10, 20, 80, 0.9)]})

    run = evaluate_detector("x", detector, images, fake_loader({"a.png": 0}), near_far_height=50)

    assert run.detections["a.png"] == [Detection(10, 10, 20, 80, 0.9)]
