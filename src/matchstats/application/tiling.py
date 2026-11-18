"""Kachel-Variante: ein beliebiger Detektor läuft auf überlappenden Bildausschnitten."""

import numpy as np

from matchstats.application.detector import Detector
from matchstats.domain.detection import Detection, non_max_suppression
from matchstats.domain.tiling import tile_rects


class TiledDetector:
    """Verpackt einen Detektor: Kacheln erkennen, Boxen zurückrechnen, Doppelte zusammenführen."""

    def __init__(self, inner: Detector, tile_size: int, overlap: float, nms_iou: float) -> None:
        self._inner = inner
        self._tile_size = tile_size
        self._overlap = overlap
        self._nms_iou = nms_iou

    def detect(self, image: np.ndarray) -> list[Detection]:
        height, width = image.shape[:2]
        found: list[Detection] = []
        for x, y, w, h in tile_rects(width, height, self._tile_size, self._overlap):
            for d in self._inner.detect(image[y : y + h, x : x + w]):
                found.append(Detection(d.x + x, d.y + y, d.w, d.h, d.score))
        return non_max_suppression(found, self._nms_iou)
