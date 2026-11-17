"""Abnahmetest T2: Das echte Testset (60 beschriftete Bilder) hat das richtige Format.

Die Datei liegt lokal in data/testset/coco.json (nicht im Git). Fehlt sie, wird übersprungen.
"""

import json
from collections import Counter
from pathlib import Path

import pytest

from matchstats.domain.testset import CLASSES
from matchstats.infrastructure.testset_loader import load_testset

COCO = Path(__file__).resolve().parents[1] / "data" / "testset" / "coco.json"

pytestmark = pytest.mark.skipif(
    not COCO.is_file(),
    reason="data/testset/coco.json fehlt (lokal, nicht im Git)",
)


def test_real_testset_has_exactly_60_images():
    assert len(load_testset(COCO)) == 60


def test_real_testset_has_20_images_per_clip():
    counts = Counter(i.file_name.split("_f")[0] for i in load_testset(COCO))

    assert counts == {"clip1": 20, "clip2": 20, "clip3": 20}


def test_real_testset_boxes_use_only_the_four_classes():
    for image in load_testset(COCO):
        for box in image.boxes:
            assert box.label in CLASSES


def test_real_testset_has_at_least_one_box_in_every_image():
    empty = [i.file_name for i in load_testset(COCO) if not i.boxes]

    assert empty == []


def test_real_testset_contains_all_four_classes():
    used = {b.label for i in load_testset(COCO) for b in i.boxes}

    assert used == set(CLASSES)


def test_real_testset_passes_format_check_without_error():
    load_testset(COCO)  # wirft TestsetFormatError bei Formatverstoß


def test_real_testset_category_names_are_the_four_classes():
    data = json.loads(COCO.read_text(encoding="utf-8"))

    assert {c["name"] for c in data["categories"]} <= set(CLASSES)
