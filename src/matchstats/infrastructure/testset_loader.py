"""Liest das beschriftete Testset (COCO-JSON, z. B. aus Label Studio) und prüft es streng."""

import json
import math
import re
from pathlib import Path

from matchstats.domain.testset import CLASSES, LabeledBox, LabeledImage

# Erwartete Bildgröße (Breite, Höhe) der Testbilder.
EXPECTED_SIZE: tuple[int, int] = (1920, 1080)

# Erlaubte Überschreitung des Bildrands je Kante in Pixeln.
EDGE_TOLERANCE = 1

# Label Studio setzt Präfixe vor den Namen; nur dieses Muster am Ende zählt.
_NAME_PATTERN = re.compile(r"clip\d+_f\d{5}\.png$")


class TestsetFormatError(ValueError):
    """Das Testset verletzt das vereinbarte Format."""

    __test__ = False  # kein pytest-Testfall, auch wenn der Name mit "Test" beginnt


def _normalize_name(raw: str) -> str:
    match = _NAME_PATTERN.search(raw)
    if match is None:
        raise TestsetFormatError(f"Dateiname passt nicht zum Muster clipN_fNNNNN.png: {raw!r}")
    return match.group(0)


def _need(obj: object, key: str, kind: type | tuple[type, ...], where: str):
    """Holt einen Pflichtwert aus einem Objekt und prüft den Typ (bool zählt nie als Zahl)."""
    if not isinstance(obj, dict):
        raise TestsetFormatError(f"{where}: Objekt erwartet")
    if key not in obj:
        raise TestsetFormatError(f"{where}: Schlüssel {key!r} fehlt")
    value = obj[key]
    if isinstance(value, bool) or not isinstance(value, kind):
        raise TestsetFormatError(f"{where}: Schlüssel {key!r} hat falschen Typ")
    return value


def _parse_bbox(raw: object, name: str) -> tuple[float, float, float, float]:
    if not isinstance(raw, list) or len(raw) != 4:
        raise TestsetFormatError(f"{name}: bbox muss eine Liste aus 4 Zahlen sein")
    values: list[float] = []
    for v in raw:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
            raise TestsetFormatError(f"{name}: bbox enthält ungültigen Wert {v!r}")
        values.append(v)
    return values[0], values[1], values[2], values[3]


def _check_box(box: LabeledBox, width: int, height: int, name: str) -> None:
    if box.w <= 0 or box.h <= 0:
        raise TestsetFormatError(f"{name}: Box mit Breite/Höhe <= 0")
    # Rundung beim Export: jede Kante darf höchstens 1 Pixel über den Rand ragen.
    if (
        box.x < -EDGE_TOLERANCE
        or box.y < -EDGE_TOLERANCE
        or box.x + box.w > width + EDGE_TOLERANCE
        or box.y + box.h > height + EDGE_TOLERANCE
    ):
        raise TestsetFormatError(f"{name}: Box liegt außerhalb des Bildes")


def load_testset(
    path: Path, expected_size: tuple[int, int] | None = EXPECTED_SIZE
) -> list[LabeledImage]:
    """Lädt das Testset. `expected_size=None` schaltet die Größenprüfung ab.

    Jede Formatverletzung führt zu TestsetFormatError.
    """
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except ValueError as err:  # auch JSONDecodeError und UnicodeDecodeError
        raise TestsetFormatError(f"Datei ist kein gültiges JSON: {err}") from err
    if not isinstance(data, dict):
        raise TestsetFormatError("Wurzel der Datei muss ein Objekt sein")

    label_by_category: dict[int, str] = {}
    for cat in _need(data, "categories", list, "Datei"):
        cat_name = _need(cat, "name", str, "Kategorie")
        cat_id = _need(cat, "id", int, "Kategorie")
        if cat_name not in CLASSES:
            raise TestsetFormatError(f"Unbekannte Klasse: {cat_name!r}")
        if cat_id in label_by_category:
            raise TestsetFormatError(f"Kategorie-ID doppelt: {cat_id}")
        label_by_category[cat_id] = cat_name

    images: dict[int, dict] = {}
    names: set[str] = set()
    for img in _need(data, "images", list, "Datei"):
        name = _normalize_name(_need(img, "file_name", str, "Bild"))
        img_id = _need(img, "id", int, name)
        if img_id in images:
            raise TestsetFormatError(f"Bild-ID doppelt: {img_id}")
        if name in names:
            raise TestsetFormatError(f"Bild doppelt vorhanden: {name}")
        names.add(name)
        size = (_need(img, "width", int, name), _need(img, "height", int, name))
        if expected_size is not None and size != expected_size:
            raise TestsetFormatError(f"{name}: Größe {size}, erwartet {expected_size}")
        images[img_id] = {"name": name, "width": size[0], "height": size[1], "boxes": []}

    for ann in _need(data, "annotations", list, "Datei"):
        image_id = _need(ann, "image_id", int, "Beschriftung")
        category_id = _need(ann, "category_id", int, "Beschriftung")
        if "bbox" not in ann:
            raise TestsetFormatError("Beschriftung: Schlüssel 'bbox' fehlt")
        target = images.get(image_id)
        if target is None:
            raise TestsetFormatError(f"Beschriftung zu unbekanntem Bild: {image_id}")
        label = label_by_category.get(category_id)
        if label is None:
            raise TestsetFormatError(f"Unbekannte Kategorie-ID: {category_id}")
        x, y, w, h = _parse_bbox(ann["bbox"], target["name"])
        box = LabeledBox(x, y, w, h, label)
        _check_box(box, target["width"], target["height"], target["name"])
        target["boxes"].append(box)

    return [
        LabeledImage(i["name"], i["width"], i["height"], tuple(i["boxes"])) for i in images.values()
    ]
