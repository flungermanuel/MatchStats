"""T2: Das Dateiformat des Testsets (COCO-JSON) wird streng geprüft. Nur künstliche Daten."""

import json

import pytest

from matchstats.domain.testset import CLASSES, LabeledBox, LabeledImage
from matchstats.infrastructure.testset_loader import TestsetFormatError, load_testset

CATEGORIES = [
    {"id": 1, "name": "team_a"},
    {"id": 2, "name": "team_b"},
    {"id": 3, "name": "goalkeeper"},
    {"id": 4, "name": "referee"},
]


def _image(id_=1, name="clip1_f00010.png", w=1920, h=1080):
    return {"id": id_, "file_name": name, "width": w, "height": h}


def _ann(id_=1, image_id=1, category_id=1, bbox=(100, 200, 50, 120)):
    return {"id": id_, "image_id": image_id, "category_id": category_id, "bbox": list(bbox)}


def _write(tmp_path, images=None, annotations=None, categories=None):
    data = {
        "images": [_image()] if images is None else images,
        "annotations": [_ann()] if annotations is None else annotations,
        "categories": CATEGORIES if categories is None else categories,
    }
    path = tmp_path / "coco.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def test_classes_are_the_four_agreed_labels():
    assert CLASSES == ("team_a", "team_b", "goalkeeper", "referee")


def test_valid_testset_is_loaded_with_boxes_and_classes(tmp_path):
    images = [_image(1, "clip1_f00010.png"), _image(2, "clip2_f00030.png")]
    anns = [
        _ann(1, 1, 1, (100, 200, 50, 120)),
        _ann(2, 1, 4, (10, 20, 30, 60)),
        _ann(3, 2, 3, (500, 400, 40, 100)),
    ]

    result = load_testset(_write(tmp_path, images, anns))

    assert len(result) == 2
    first = next(i for i in result if i.file_name == "clip1_f00010.png")
    assert isinstance(first, LabeledImage)
    assert (first.width, first.height) == (1920, 1080)
    assert LabeledBox(100, 200, 50, 120, "team_a") in first.boxes
    assert LabeledBox(10, 20, 30, 60, "referee") in first.boxes
    assert len(first.boxes) == 2


def test_class_is_assigned_by_category_name_not_by_id(tmp_path):
    swapped = [
        {"id": 4, "name": "team_a"},
        {"id": 3, "name": "team_b"},
        {"id": 2, "name": "goalkeeper"},
        {"id": 1, "name": "referee"},
    ]
    anns = [_ann(1, 1, 4), _ann(2, 1, 1, (300, 300, 40, 90))]

    result = load_testset(_write(tmp_path, annotations=anns, categories=swapped))

    assert [b.label for b in result[0].boxes] == ["team_a", "referee"]


def test_unknown_category_name_is_rejected(tmp_path):
    cats = [*CATEGORIES, {"id": 9, "name": "ball"}]
    path = _write(tmp_path, annotations=[_ann(category_id=9)], categories=cats)

    with pytest.raises(TestsetFormatError):
        load_testset(path)


@pytest.mark.parametrize(
    "exported",
    [
        "abc123-clip1_f00010.png",
        "images/clip1_f00010.png",
        "/data/local-files/?d=frames/clip1_f00010.png",
        "clip1_f00010.png",
        # echter COCO-Export von Label Studio unter Windows (Pfad relativ, mit Backslashes)
        "..\\..\\Desktop\\projekt\\data\\labelstudio\\media\\upload\\2\\a767ca85-clip1_f00010.png",
    ],
)
def test_label_studio_prefixes_are_normalized_to_pattern_suffix(tmp_path, exported):
    result = load_testset(_write(tmp_path, images=[_image(name=exported)]))

    assert result[0].file_name == "clip1_f00010.png"


@pytest.mark.parametrize(
    "bad", ["foto.png", "clip1_f10.png", "clip1_f00010.jpg", "clipX_f00010.png"]
)
def test_file_name_not_matching_pattern_is_rejected(tmp_path, bad):
    with pytest.raises(TestsetFormatError):
        load_testset(_write(tmp_path, images=[_image(name=bad)], annotations=[]))


def test_two_images_with_same_normalized_name_are_rejected(tmp_path):
    images = [_image(1, "aaa-clip1_f00010.png"), _image(2, "bbb-clip1_f00010.png")]

    with pytest.raises(TestsetFormatError):
        load_testset(_write(tmp_path, images=images, annotations=[]))


def test_image_size_must_match_expected_size(tmp_path):
    path = _write(tmp_path, images=[_image(w=1280, h=720)], annotations=[])

    with pytest.raises(TestsetFormatError):
        load_testset(path)


def test_image_size_check_can_be_disabled_with_none(tmp_path):
    path = _write(
        tmp_path, images=[_image(w=320, h=180)], annotations=[_ann(bbox=(10, 10, 20, 40))]
    )

    result = load_testset(path, expected_size=None)

    assert (result[0].width, result[0].height) == (320, 180)


@pytest.mark.parametrize(
    "bbox",
    [
        (100, 100, 0, 50),  # Breite 0
        (100, 100, 50, 0),  # Höhe 0
        (100, 100, -5, 50),  # negative Breite
        (100, 100, 50, -5),  # negative Höhe
        (-10, 100, 50, 50),  # links außerhalb
        (100, -10, 50, 50),  # oben außerhalb
        (1900, 100, 50, 50),  # rechts außerhalb (1950 > 1920)
        (100, 1050, 50, 50),  # unten außerhalb (1100 > 1080)
    ],
)
def test_invalid_box_is_rejected(tmp_path, bbox):
    with pytest.raises(TestsetFormatError):
        load_testset(_write(tmp_path, annotations=[_ann(bbox=bbox)]))


def test_box_touching_the_image_border_is_accepted(tmp_path):
    result = load_testset(_write(tmp_path, annotations=[_ann(bbox=(1870, 1000, 50, 80))]))

    assert len(result[0].boxes) == 1


def test_annotation_with_unknown_image_id_is_rejected(tmp_path):
    with pytest.raises(TestsetFormatError):
        load_testset(_write(tmp_path, annotations=[_ann(image_id=99)]))


def test_image_without_boxes_is_allowed(tmp_path):
    result = load_testset(_write(tmp_path, annotations=[]))

    assert result[0].boxes == ()


def test_format_error_is_a_value_error():
    assert issubclass(TestsetFormatError, ValueError)


# --- Randtoleranz: höchstens 1 Pixel Überschreitung (Rundung beim Export) ---


@pytest.mark.parametrize(
    "bbox",
    [
        (1870, 1000, 51, 80),  # rechts: x+w = 1921 = Breite+1
        (100, 1000, 50, 81),  # unten: y+h = 1081 = Höhe+1
        (-1, 100, 50, 50),  # links: x = -1
        (100, -1, 50, 50),  # oben: y = -1
    ],
)
def test_box_exceeding_the_border_by_one_pixel_is_accepted(tmp_path, bbox):
    result = load_testset(_write(tmp_path, annotations=[_ann(bbox=bbox)]))

    assert len(result[0].boxes) == 1


@pytest.mark.parametrize(
    "bbox",
    [
        (1870, 1000, 51.5, 80),  # rechts: 1921.5
        (100, 1000, 50, 81.5),  # unten: 1081.5
        (-1.5, 100, 50, 50),  # links
        (100, -1.5, 50, 50),  # oben
    ],
)
def test_box_exceeding_the_border_by_more_than_one_pixel_is_rejected(tmp_path, bbox):
    with pytest.raises(TestsetFormatError):
        load_testset(_write(tmp_path, annotations=[_ann(bbox=bbox)]))


# --- Strukturfehler führen nur zu TestsetFormatError ---


def _write_raw(tmp_path, data):
    path = tmp_path / "coco.json"
    path.write_text(json.dumps(data), encoding="utf-8")
    return path


def _valid_data():
    return {"images": [_image()], "annotations": [_ann()], "categories": list(CATEGORIES)}


@pytest.mark.parametrize("bbox", [[1, 2, 3], [1, 2, 3, 4, 5], [], "abcd", None, 5])
def test_bbox_with_wrong_length_or_type_is_rejected_as_format_error(tmp_path, bbox):
    data = _valid_data()
    data["annotations"][0]["bbox"] = bbox

    with pytest.raises(TestsetFormatError):
        load_testset(_write_raw(tmp_path, data))


@pytest.mark.parametrize("bbox", [["a", 2, 3, 4], [1, None, 3, 4], [1, 2, [3], 4], [1, 2, 3, "x"]])
def test_non_numeric_bbox_values_are_rejected_as_format_error(tmp_path, bbox):
    data = _valid_data()
    data["annotations"][0]["bbox"] = bbox

    with pytest.raises(TestsetFormatError):
        load_testset(_write_raw(tmp_path, data))


@pytest.mark.parametrize("index", [0, 1, 2, 3])
def test_nan_in_bbox_is_rejected_as_format_error(tmp_path, index):
    data = _valid_data()
    data["annotations"][0]["bbox"][index] = float("nan")

    with pytest.raises(TestsetFormatError):
        load_testset(_write_raw(tmp_path, data))


@pytest.mark.parametrize(
    "path_to_remove",
    [
        ("images",),
        ("annotations",),
        ("categories",),
        ("annotations", 0, "bbox"),
        ("annotations", 0, "image_id"),
        ("annotations", 0, "category_id"),
        ("images", 0, "file_name"),
        ("images", 0, "id"),
        ("images", 0, "width"),
        ("images", 0, "height"),
        ("categories", 0, "name"),
        ("categories", 0, "id"),
    ],
)
def test_missing_keys_are_rejected_as_format_error(tmp_path, path_to_remove):
    data = _valid_data()
    target = data
    for step in path_to_remove[:-1]:
        target = target[step]
    del target[path_to_remove[-1]]

    with pytest.raises(TestsetFormatError):
        load_testset(_write_raw(tmp_path, data))


def test_duplicate_image_ids_are_rejected(tmp_path):
    images = [_image(1, "clip1_f00010.png"), _image(1, "clip1_f00030.png")]

    with pytest.raises(TestsetFormatError):
        load_testset(_write(tmp_path, images=images, annotations=[]))


def test_duplicate_category_ids_are_rejected(tmp_path):
    cats = [{"id": 1, "name": "team_a"}, {"id": 1, "name": "team_b"}]

    with pytest.raises(TestsetFormatError):
        load_testset(_write(tmp_path, annotations=[], categories=cats))
