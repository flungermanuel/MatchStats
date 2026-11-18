"""Erkennung einer Person im Bild: Datentyp, Überlappung (IoU) und Zusammenführen (NMS)."""

from dataclasses import dataclass
from typing import Protocol


class HasBox(Protocol):
    """Alles mit einer Box in Pixeln (x, y = linke obere Ecke)."""

    x: float
    y: float
    w: float
    h: float


@dataclass(frozen=True)
class Detection:
    x: float
    y: float
    w: float
    h: float
    score: float  # Sicherheit des Detektors, 0 bis 1


def iou(a: HasBox, b: HasBox) -> float:
    """Überlappung zweier Boxen: Schnittfläche geteilt durch Vereinigungsfläche."""
    inter_w = min(a.x + a.w, b.x + b.w) - max(a.x, b.x)
    inter_h = min(a.y + a.h, b.y + b.h) - max(a.y, b.y)
    if inter_w <= 0 or inter_h <= 0:
        return 0.0
    inter = inter_w * inter_h
    union = a.w * a.h + b.w * b.h - inter
    return inter / union if union > 0 else 0.0


def non_max_suppression(detections: list[Detection], iou_threshold: float) -> list[Detection]:
    """Entfernt Doppelte: Von sich stark überlappenden Boxen bleibt die mit dem höchsten Score."""
    kept: list[Detection] = []
    for candidate in sorted(detections, key=lambda d: d.score, reverse=True):
        if all(iou(candidate, k) <= iou_threshold for k in kept):
            kept.append(candidate)
    return kept
