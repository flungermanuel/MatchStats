"""Datentypen des beschrifteten Testsets (rein, keine I/O)."""

from dataclasses import dataclass

# Die vier vereinbarten Klassen.
CLASSES: tuple[str, ...] = ("team_a", "team_b", "goalkeeper", "referee")


@dataclass(frozen=True)
class LabeledBox:
    # Box in Pixeln: linke obere Ecke (x, y), Breite und Höhe.
    x: float
    y: float
    w: float
    h: float
    label: str


@dataclass(frozen=True)
class LabeledImage:
    file_name: str
    width: int
    height: int
    boxes: tuple[LabeledBox, ...]
