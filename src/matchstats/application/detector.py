"""Schnittstelle (Port) für Personen-Detektoren. Implementierungen liegen in infrastructure/."""

from typing import Protocol

import numpy as np

from matchstats.domain.detection import Detection


class Detector(Protocol):
    """Findet Personen in einem Bild.

    Eingabe: Bild als Array (Höhe x Breite x 3, RGB, uint8).
    Ausgabe: Boxen in Pixeln des übergebenen Bildes.
    """

    def detect(self, image: np.ndarray) -> list[Detection]: ...
