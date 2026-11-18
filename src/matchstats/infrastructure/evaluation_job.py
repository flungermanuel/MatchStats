"""Verdrahtet die Messung: Testset laden, Detektor-Varianten bauen, messen, Bericht und Bilder."""

from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

from matchstats.application.detector import Detector
from matchstats.application.evaluation import EvaluationRun, evaluate_detector
from matchstats.application.library import Library, LibraryError
from matchstats.application.tiling import TiledDetector
from matchstats.domain.metrics import median_height
from matchstats.domain.settings import Settings
from matchstats.domain.testset import LabeledImage
from matchstats.infrastructure.evaluation_report import write_report
from matchstats.infrastructure.image_io import load_image, save_overlay
from matchstats.infrastructure.testset_loader import load_testset

DETECTOR_NAMES = ("rfdetr", "yolo")


def _build_detector(name: str, settings: Settings) -> Detector:
    # Erst hier importieren: ein nicht installierter Detektor stört die anderen nicht.
    if name == "rfdetr":
        from matchstats.infrastructure.rfdetr_detector import RfDetrDetector

        return RfDetrDetector(settings.detector_model, settings.score_threshold)
    if name == "yolo":
        from matchstats.infrastructure.yolo_detector import YoloDetector

        return YoloDetector(settings.detector_model, settings.score_threshold)
    raise ValueError(f"Unbekannter Detektor {name!r}, erlaubt: {DETECTOR_NAMES}")


def run_evaluation(
    testset: Path,
    images_dir: Path,
    out_dir: Path,
    settings: Settings,
    detector_names: tuple[str, ...] = DETECTOR_NAMES,
    overlay_count: int = 6,
) -> list[EvaluationRun]:
    """Misst ein einzelnes Testset (alter Aufruf: coco.json plus Bilderordner)."""
    images = load_testset(testset)
    return _measure(
        images, lambda name: images_dir / name, out_dir, settings, detector_names, overlay_count
    )


def run_library_evaluation(
    library: Library,
    match_id: str,
    half: int,
    out_dir: Path,
    settings: Settings,
    detector_names: tuple[str, ...] = DETECTOR_NAMES,
    overlay_count: int = 6,
) -> list[EvaluationRun]:
    """Misst alle Clips einer Halbzeit in EINEM Bericht (eine nah/fern-Grenze über alle Bilder)."""
    images: list[LabeledImage] = []
    image_paths: dict[str, Path] = {}
    for clip in library.list_clips(match_id, half=half):
        testset_dir = library.clip_dir(match_id, clip.id) / "testset"
        coco = testset_dir / "coco.json"
        if not coco.is_file():
            continue  # Clip ohne Testset trägt nichts zur Messung bei
        for image in load_testset(coco, expected_size=(clip.width, clip.height)):
            # Schlüssel mit Clip-ID: gleiche Dateinamen in verschiedenen Clips kollidieren nicht.
            key = f"{clip.id}/{image.file_name}"
            image_paths[key] = testset_dir / "images" / image.file_name
            images.append(replace(image, file_name=key))
    if not images:
        raise LibraryError(f"Spiel {match_id}: keine Clips mit Testset in Halbzeit {half}")
    return _measure(
        images, image_paths.__getitem__, out_dir, settings, detector_names, overlay_count
    )


def _measure(
    images: list[LabeledImage],
    image_path: Callable[[str], Path],
    out_dir: Path,
    settings: Settings,
    detector_names: tuple[str, ...],
    overlay_count: int,
) -> list[EvaluationRun]:
    """Misst jeden Detektor als Ganzbild und als Kacheln; schreibt Bericht und Beispielbilder."""
    border = median_height([list(i.boxes) for i in images])
    by_name = {i.file_name: i for i in images}
    step = max(1, len(images) // max(overlay_count, 1))
    overlay_names = [i.file_name for i in images[::step]][:overlay_count]

    runs: list[EvaluationRun] = []
    for name in detector_names:
        detector = _build_detector(name, settings)
        variants = {
            f"{name}-whole": detector,
            f"{name}-tiles": TiledDetector(
                detector, settings.tile_size, settings.tile_overlap, settings.nms_iou
            ),
        }
        for variant, instance in variants.items():
            print(f"Messe {variant} ...", flush=True)
            run = evaluate_detector(
                variant,
                instance,
                images,
                lambda file_name: load_image(image_path(file_name)),
                border,
            )
            runs.append(run)
            for file_name in overlay_names:
                save_overlay(
                    load_image(image_path(file_name)),
                    list(by_name[file_name].boxes),
                    run.detections[file_name],
                    out_dir / "overlays" / variant / file_name,
                )
    write_report(runs, out_dir)
    return runs
