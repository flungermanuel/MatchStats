"""Kachel-Geometrie und Zusammenführen (ohne echtes Modell, mit Fake-Detektor)."""

import numpy as np
import pytest

from matchstats.application.tiling import TiledDetector
from matchstats.domain.detection import Detection
from matchstats.domain.tiling import tile_rects


def test_tiles_cover_the_whole_image_for_full_hd():
    rects = tile_rects(1920, 1080, tile_size=640, overlap=0.2)

    assert len(rects) == 8  # 4 Spalten x 2 Zeilen
    assert max(x + w for x, _, w, _ in rects) == 1920
    assert max(y + h for _, y, _, h in rects) == 1080
    assert all(w == 640 and h == 640 for _, _, w, h in rects)


def test_tiles_overlap_by_at_least_the_requested_share():
    xs = sorted({x for x, _, _, _ in tile_rects(1920, 1080, 640, 0.2)})

    assert all(640 - (b - a) >= 0.2 * 640 - 1 for a, b in zip(xs, xs[1:], strict=False))


def test_small_image_gives_a_single_tile_of_image_size():
    assert tile_rects(300, 200, tile_size=640, overlap=0.2) == [(0, 0, 300, 200)]


def test_overlap_must_be_below_one():
    with pytest.raises(ValueError):
        tile_rects(1920, 1080, 640, 1.0)


class FakeDetector:
    """Findet eine feste Box im Bild, an der Stelle, an der ein heller Block liegt."""

    def detect(self, image: np.ndarray) -> list[Detection]:
        ys, xs = np.where(image[:, :, 0] > 200)
        if len(xs) == 0:
            return []
        x0, x1, y0, y1 = xs.min(), xs.max() + 1, ys.min(), ys.max() + 1
        return [Detection(float(x0), float(y0), float(x1 - x0), float(y1 - y0), 0.9)]


def test_tiled_detector_reports_boxes_in_full_image_coordinates():
    image = np.zeros((1080, 1920, 3), dtype=np.uint8)
    image[700:760, 1500:1530] = 255  # Spieler weit rechts unten
    tiled = TiledDetector(FakeDetector(), tile_size=640, overlap=0.2, nms_iou=0.5)

    found = tiled.detect(image)

    assert len(found) >= 1
    assert any(
        d.x == pytest.approx(1500) and d.y == pytest.approx(700) and d.w == 30 and d.h == 60
        for d in found
    )


def test_tiled_detector_merges_duplicate_from_overlapping_tiles():
    image = np.zeros((1080, 1920, 3), dtype=np.uint8)
    image[300:360, 600:630] = 255  # liegt im Überlappungsbereich zweier Kacheln (512..640)
    tiled = TiledDetector(FakeDetector(), tile_size=640, overlap=0.2, nms_iou=0.5)

    assert len(tiled.detect(image)) == 1
