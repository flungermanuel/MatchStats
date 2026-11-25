"""Port für die Teamzuordnung (Implementierung in infrastructure/)."""

from collections.abc import Sequence
from typing import Protocol

import numpy as np

from matchstats.domain.detection import HasBox
from matchstats.domain.teams import TeamPrediction


class TeamClassifier(Protocol):
    def classify(
        self, images: Sequence[np.ndarray], boxes: Sequence[HasBox]
    ) -> list[TeamPrediction]:
        """Teamklasse je Box. Box i liegt in Bild i (RGB); dasselbe Bild darf mehrfach vorkommen.

        Die Rückgabe hat dieselbe Länge und Reihenfolge wie `boxes`. Nicht bestimmbare Boxen
        bekommen TeamPrediction(None, None).
        """
        ...
