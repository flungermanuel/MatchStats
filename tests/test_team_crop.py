"""T5b1 Pflichttest: Farbmerkmal auf Ganzbild und auf crop_box-Ausschnitt ist gleich.

Vertrag (angenommen): crop_box(image, box) -> (Ausschnitt, verschobene Box). Der Ausschnitt
enthält die GANZE Box, auf die Bildgrenzen gekürzt; sein Ursprung ist ganzzahlig und gerade.

Synthetisches Bild: Rasen, zwei Trikotfarben, Boxen teils am oder über dem Bildrand, teils mit
.5-Koordinaten (die Rundung darf durch das Verschieben der Box nicht kippen).
"""

import numpy as np

from matchstats.application.team_stage import crop_box
from matchstats.domain.detection import Detection
from matchstats.domain.settings import Settings
from matchstats.infrastructure.color_team_classifier import ColorTeamClassifier

GRASS = (60, 160, 60)
RED = (200, 30, 30)
BLUE = (30, 40, 200)
SHORTS = (20, 20, 20)
WIDTH, HEIGHT = 320, 260


def paint_player(image, box, color, seed):
    """Oberkörper in Trikotfarbe, unten dunkel; was außerhalb des Bildes liegt, entfällt."""
    rng = np.random.default_rng(seed)
    x0, y0 = round(box.x), round(box.y)
    w, h = round(box.w), round(box.h)
    patch = np.empty((h, w, 3), np.uint8)
    patch[: h // 2] = color
    patch[h // 2 :] = SHORTS
    patch = np.clip(patch.astype(int) + rng.integers(-3, 4, patch.shape), 0, 255).astype(np.uint8)
    ys, xs = slice(max(0, y0), min(HEIGHT, y0 + h)), slice(max(0, x0), min(WIDTH, x0 + w))
    image[ys, xs] = patch[ys.start - y0 : ys.stop - y0, xs.start - x0 : xs.stop - x0]


def scene():
    image = np.empty((HEIGHT, WIDTH, 3), np.uint8)
    image[:] = GRASS
    boxes = [
        Detection(10.0, 10.0, 40.0, 100.0, 1.0),  # innen
        Detection(70.5, 12.5, 40.0, 100.0, 1.0),  # .5-Koordinaten
        Detection(131.5, 11.0, 40.0, 100.0, 1.0),  # .5 nur in x
        Detection(-12.0, 130.0, 40.0, 100.0, 1.0),  # ragt links heraus
        Detection(60.0, -30.0, 40.0, 100.0, 1.0),  # ragt oben heraus
        Detection(290.5, 140.0, 40.0, 100.0, 1.0),  # ragt rechts heraus, .5
        Detection(200.0, 200.5, 40.0, 100.0, 1.0),  # ragt unten heraus
        Detection(150.0, 130.5, 40.0, 100.0, 1.0),  # innen
        Detection(231.0, 15.0, 40.0, 100.0, 1.0),  # ungerade Koordinate
        Detection(105.5, 135.5, 40.0, 100.0, 1.0),  # .5 in x und y
    ]
    for i, box in enumerate(boxes):
        paint_player(image, box, RED if i % 2 == 0 else BLUE, seed=i)
    return image, boxes


def test_classify_on_crops_equals_classify_on_whole_image():
    image, boxes = scene()
    classifier = ColorTeamClassifier(Settings())

    whole = classifier.classify([image] * len(boxes), boxes)
    crops = [crop_box(image, box) for box in boxes]
    cropped = classifier.classify([c[0] for c in crops], [c[1] for c in crops])

    assert cropped == whole
    assert {"team_a", "team_b"} <= {p.label for p in whole}  # nicht trivial (nicht alles unbekannt)


def test_crop_origin_is_even_integer_and_crop_fits_into_the_image():
    image, boxes = scene()

    for box in boxes:
        crop, shifted = crop_box(image, box)
        ox, oy = box.x - shifted.x, box.y - shifted.y
        assert ox == int(ox) and oy == int(oy)
        assert int(ox) % 2 == 0 and int(oy) % 2 == 0
        assert crop.shape[0] <= image.shape[0] and crop.shape[1] <= image.shape[1]
        assert crop.shape[2] == 3


def test_crop_is_the_image_region_around_the_whole_box_and_keeps_box_size():
    image, _ = scene()
    box = Detection(100.0, 50.0, 40.0, 100.0, 0.7)

    crop, shifted = crop_box(image, box)

    assert (shifted.w, shifted.h, shifted.score) == (box.w, box.h, box.score)
    assert shifted.x >= 0 and shifted.y >= 0
    assert shifted.x + shifted.w <= crop.shape[1]
    assert shifted.y + shifted.h <= crop.shape[0]
    x0, y0 = round(box.x - shifted.x), round(box.y - shifted.y)
    assert np.array_equal(crop, image[y0 : y0 + crop.shape[0], x0 : x0 + crop.shape[1]])


def test_crop_of_box_sticking_out_of_the_image_is_clipped_to_the_image():
    image, _ = scene()
    box = Detection(-12.0, -30.0, 40.0, 100.0, 1.0)

    crop, _shifted = crop_box(image, box)

    assert crop.shape[0] >= 70 and crop.shape[1] >= 28  # sichtbarer Teil der Box ist enthalten
    assert crop.shape[0] <= image.shape[0] and crop.shape[1] <= image.shape[1]


def test_crop_is_a_copy_and_does_not_keep_the_whole_frame_alive():
    image = np.zeros((120, 160, 3), dtype=np.uint8)
    crop, _ = crop_box(image, Detection(x=40, y=30, w=20, h=50, score=0.9))
    assert crop.flags.owndata
    assert not np.shares_memory(crop, image)
