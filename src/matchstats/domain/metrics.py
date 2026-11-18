"""Messregeln der Spezifikation: Treffer, Recall, Precision, nah/fern (rein, keine I/O).

- Treffer: IoU mindestens 0,5; jede beschriftete Box kann nur einmal getroffen werden.
- Recall = getroffene Beschriftungen / alle Beschriftungen.
- Precision = Treffer / alle Erkennungen.
- Nah/fern: Recall getrennt nach Boxhöhe der Beschriftung (nah = Höhe >= Grenze).
"""

from dataclasses import dataclass
from statistics import median

from matchstats.domain.detection import Detection, iou
from matchstats.domain.testset import LabeledBox

HIT_IOU = 0.5


@dataclass(frozen=True)
class ImageResult:
    """Zählwerte eines Bildes."""

    detections: int
    true_positives: int
    labels_near: int
    labels_far: int
    hits_near: int
    hits_far: int


@dataclass(frozen=True)
class Summary:
    """Kennzahlen über mehrere Bilder. `None` heißt: nicht berechenbar (nicht 0)."""

    images: int
    labels: int
    detections: int
    true_positives: int
    labels_near: int
    labels_far: int
    recall: float | None
    precision: float | None
    recall_near: float | None
    recall_far: float | None


def median_height(labels_per_image: list[list[LabeledBox]]) -> float:
    """Median der Boxhöhen aller Beschriftungen (Grenze für nah/fern)."""
    heights = [box.h for labels in labels_per_image for box in labels]
    if not heights:
        raise ValueError("keine Beschriftungen vorhanden")
    return float(median(heights))


def matched_labels(detections: list[Detection], labels: list[LabeledBox]) -> set[int]:
    """Indizes der getroffenen Beschriftungen (Reihenfolge nach Score, je Box nur einmal)."""
    taken: set[int] = set()
    for d in sorted(detections, key=lambda d: d.score, reverse=True):
        best, best_iou = None, HIT_IOU
        for i, label in enumerate(labels):
            if i in taken:
                continue
            value = iou(d, label)
            if value >= best_iou:
                best, best_iou = i, value
        if best is not None:
            taken.add(best)
    return taken


def evaluate_image(
    detections: list[Detection], labels: list[LabeledBox], near_far_height: float
) -> ImageResult:
    """Zählt Treffer, Erkennungen und Beschriftungen eines Bildes (nah/fern getrennt)."""
    taken = matched_labels(detections, labels)
    near = {i for i, label in enumerate(labels) if label.h >= near_far_height}
    return ImageResult(
        detections=len(detections),
        true_positives=len(taken),
        labels_near=len(near),
        labels_far=len(labels) - len(near),
        hits_near=len(taken & near),
        hits_far=len(taken - near),
    )


def _ratio(part: int, whole: int) -> float | None:
    return part / whole if whole > 0 else None


def summarize(results: list[ImageResult]) -> Summary:
    detections = sum(r.detections for r in results)
    hits = sum(r.true_positives for r in results)
    near = sum(r.labels_near for r in results)
    far = sum(r.labels_far for r in results)
    return Summary(
        images=len(results),
        labels=near + far,
        detections=detections,
        true_positives=hits,
        labels_near=near,
        labels_far=far,
        recall=_ratio(hits, near + far),
        precision=_ratio(hits, detections),
        recall_near=_ratio(sum(r.hits_near for r in results), near),
        recall_far=_ratio(sum(r.hits_far for r in results), far),
    )
