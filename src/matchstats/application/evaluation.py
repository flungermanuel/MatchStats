"""Auswertungsstufe: misst einen Detektor auf beschrifteten Bildern (Recall, Precision, Zeit)."""

import time
from collections.abc import Callable
from dataclasses import dataclass

import numpy as np

from matchstats.application.detector import Detector
from matchstats.domain.detection import Detection
from matchstats.domain.metrics import Summary, evaluate_image, summarize
from matchstats.domain.testset import LabeledImage


@dataclass(frozen=True)
class EvaluationRun:
    """Ergebnis einer Detektor-Variante auf dem Testset."""

    name: str
    summary: Summary
    seconds_per_image: float
    near_far_height: float
    detections: dict[str, list[Detection]]  # je Bildname, für Ausgabebilder


def evaluate_detector(
    name: str,
    detector: Detector,
    images: list[LabeledImage],
    load_image: Callable[[str], np.ndarray],
    near_far_height: float,
) -> EvaluationRun:
    """Lässt den Detektor über alle Bilder laufen und misst nach den Regeln der Spezifikation."""
    results = []
    detections: dict[str, list[Detection]] = {}
    total_seconds = 0.0
    if images:
        # Aufwärmlauf: der erste Aufruf lädt/initialisiert intern und würde die Zeit verfälschen.
        detector.detect(load_image(images[0].file_name))
    for labeled in images:
        pixels = load_image(labeled.file_name)  # Laden zählt nicht zur Erkennungszeit
        start = time.perf_counter()
        found = detector.detect(pixels)
        total_seconds += time.perf_counter() - start
        detections[labeled.file_name] = found
        results.append(evaluate_image(found, list(labeled.boxes), near_far_height))
    return EvaluationRun(
        name=name,
        summary=summarize(results),
        seconds_per_image=total_seconds / len(images) if images else 0.0,
        near_far_height=near_far_height,
        detections=detections,
    )
