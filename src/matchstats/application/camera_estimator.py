"""Port für die Schätzung der Kamerabewegung (Implementierung in infrastructure/)."""

from collections.abc import Iterable
from typing import Protocol

import numpy as np

from matchstats.domain.camera import CameraMotion


class CameraMotionEstimator(Protocol):
    def estimate(self, images: Iterable[tuple[int, np.ndarray]]) -> list[CameraMotion]:
        """Bewegung von Bild i-1 nach Bild i für jedes Bild ab dem zweiten (Index ab 1).

        `images` liefert (Index, RGB-Bild) aufsteigend und bildweise.
        """
        ...
