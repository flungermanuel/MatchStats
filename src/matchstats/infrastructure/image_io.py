"""Bilder von der Platte lesen und Ausgabebilder mit Boxen zeichnen (Pillow)."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from matchstats.domain.detection import Detection
from matchstats.domain.metrics import matched_labels
from matchstats.domain.teams import TeamPrediction
from matchstats.domain.testset import LabeledBox

_GREEN, _YELLOW, _RED = (40, 200, 60), (255, 220, 0), (255, 50, 50)


def load_image(path: Path) -> np.ndarray:
    """Liest ein Bild als RGB-Array (Höhe x Breite x 3, uint8)."""
    with Image.open(path) as img:
        return np.array(img.convert("RGB"))


def _rect(draw: ImageDraw.ImageDraw, box, color, width: int) -> None:
    draw.rectangle([box.x, box.y, box.x + box.w, box.y + box.h], outline=color, width=width)


def save_overlay(
    image: np.ndarray, labels: list[LabeledBox], detections: list[Detection], target: Path
) -> None:
    """Zeichnet Beschriftungen und Erkennungen ins Bild.

    Grün = beschriftet und getroffen, Gelb = beschriftet aber verpasst, Rot = Erkennung.
    """
    hit = matched_labels(detections, labels)
    canvas = Image.fromarray(image)
    draw = ImageDraw.Draw(canvas)
    for i, label in enumerate(labels):
        _rect(draw, label, _GREEN if i in hit else _YELLOW, 3)
    for d in detections:
        _rect(draw, d, _RED, 1)
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)


_TEAM_COLORS = {
    "team_a": (60, 120, 255),
    "team_b": (255, 160, 0),
    "goalkeeper": (180, 80, 220),
    "referee": (240, 240, 240),
}


_FALLBACK_COLOR = (128, 128, 128)


def save_team_overlay(
    image: np.ndarray,
    labels: list[LabeledBox],
    predictions: list[TeamPrediction],
    target: Path,
) -> None:
    """Zeichnet je Box die wahre Klasse als Farbe; falsche oder unbekannte Vorhersagen rot."""
    canvas = Image.fromarray(image)
    draw = ImageDraw.Draw(canvas)
    for label, prediction in zip(labels, predictions, strict=True):
        wrong = prediction.label != label.label
        _rect(draw, label, _RED if wrong else _TEAM_COLORS.get(label.label, _FALLBACK_COLOR), 3)
    target.parent.mkdir(parents=True, exist_ok=True)
    canvas.save(target)
