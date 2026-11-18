"""Einmalige Migration der T3-Daten in die Bibliothek (T3b). Nicht Teil der CLI.

Aufruf (im Projektordner):  python tools/migrate_t3b.py [--library data/library]

Legt spiel-001 an, importiert data/clips/clip1..clip3 per Kopie (1. Halbzeit), teilt
data/testset/coco.json je Clip auf und kopiert die T3-Ergebnisse (data/ergebnis/t3) in einen
Lauf von clip1 (Unterordner "t3-ergebnis", sie gelten für alle drei Clips zusammen).
Alte Ordner werden nur gelesen, nie verändert oder gelöscht.
Nicht wiederholbar: Bricht das Skript ab, vor einem neuen Versuch data/library/spiel-001 von Hand
entfernen (spiel-001 existiert sonst schon).
"""

import argparse
import json
import re
import shutil
from dataclasses import asdict
from pathlib import Path

from matchstats.domain.library import Match, RecordingProfile
from matchstats.infrastructure.config_loader import load_settings
from matchstats.infrastructure.file_library import FileLibrary

MATCH_ID = "spiel-001"
CLIP_IDS = ("clip1", "clip2", "clip3")
PROFILE = RecordingProfile(
    angle="tribuene_hoch", camera_motion="schwenkt_und_zoomt", notes="Migration aus T3"
)
_NAME = re.compile(r"(clip\d+)_f\d{5}\.png$")


def split_coco(coco: dict, clip_id: str) -> dict:
    """Je Clip ein COCO: nur dessen Bilder und deren Beschriftungen, Dateinamen ohne Pfad."""
    images = []
    for image in coco["images"]:
        match = _NAME.search(image["file_name"])
        if match and match.group(1) == clip_id:
            images.append({**image, "file_name": match.group(0)})
    ids = {image["id"] for image in images}
    return {
        "categories": coco["categories"],
        "images": images,
        "annotations": [a for a in coco["annotations"] if a["image_id"] in ids],
    }


def migrate(root: Path, library_dir: Path) -> None:
    clips_dir = root / "data" / "clips"
    testset_dir = root / "data" / "testset"
    results_dir = root / "data" / "ergebnis" / "t3"
    library = FileLibrary(library_dir)
    library.add_match(Match(id=MATCH_ID, name="Ligaspiel 1", date=None, notes="Migration aus T3"))

    coco = json.loads((testset_dir / "coco.json").read_text(encoding="utf-8"))
    parts = {clip_id: split_coco(coco, clip_id) for clip_id in CLIP_IDS}
    # Kein Bild darf beim Aufteilen verloren gehen (sonst stimmen die Zahlen nicht mehr)
    if sum(len(p["images"]) for p in parts.values()) != len(coco["images"]):
        raise SystemExit("Fehler: Nicht alle Testbilder ließen sich einem Clip zuordnen.")
    for clip_id in CLIP_IDS:
        library.import_clip(MATCH_ID, clips_dir / f"{clip_id}.mp4", clip_id, 1, PROFILE, {})
        part = parts[clip_id]
        target = library.clip_dir(MATCH_ID, clip_id) / "testset"
        (target / "images").mkdir(parents=True)
        for image in part["images"]:
            shutil.copy2(testset_dir / "images" / image["file_name"], target / "images")
        (target / "coco.json").write_text(json.dumps(part, indent=2), encoding="utf-8")
        print(f"{clip_id}: {len(part['images'])} Bilder, {len(part['annotations'])} Beschriftungen")

    run = library.create_run(MATCH_ID, "clip1", asdict(load_settings()))
    destination = library.run_dir(MATCH_ID, "clip1", run.id) / "t3-ergebnis"
    shutil.copytree(results_dir, destination)
    print(f"T3-Ergebnisse (alle Clips) kopiert nach {destination}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--library", type=Path, default=Path("data/library"))
    args = parser.parse_args()
    migrate(Path.cwd(), args.library)


if __name__ == "__main__":
    main()
