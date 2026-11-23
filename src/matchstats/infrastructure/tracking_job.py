"""Verdrahtet den Track-Lauf: Bibliothek, Lauf, Detektor, Stufen, Darstellung, summary.json."""

import time
from dataclasses import asdict, dataclass
from importlib import metadata
from pathlib import Path
from typing import Any

import numpy as np

from matchstats.application.detector import Detector
from matchstats.application.library import Library, LibraryError
from matchstats.application.tiling import TiledDetector
from matchstats.application.track_summary import (
    summarize_id_switch_candidates,
    summarize_tracks,
)
from matchstats.application.tracker import ByteTrackLikeTracker
from matchstats.application.tracking_stages import detect_stage, track_stage
from matchstats.domain.detection import Detection
from matchstats.domain.id_switch import find_id_switch_candidates
from matchstats.domain.settings import Settings
from matchstats.infrastructure.config_loader import load_settings
from matchstats.infrastructure.json_io import write_json_atomic
from matchstats.infrastructure.stage_files import FileStageStore
from matchstats.infrastructure.track_render import render_tracks
from matchstats.infrastructure.video_source import OpenCvFrameSource

VARIANTS = ("whole", "tiles")
SUMMARY_FILE = "summary.json"
SUMMARY_SCHEMA_VERSION = 2  # 2: Kennzahlen zu ID-Wechsel-Kandidaten ergänzt
SWITCH_FILE = "id_switch_candidates.json"
SWITCH_SCHEMA_VERSION = 1
# Bibliotheken, deren Version im Ergebnis festgehalten wird (nur wenn installiert).
_TRACKED_PACKAGES = ("numpy", "scipy", "opencv-python", "opencv-python-headless", "rfdetr", "torch")


@dataclass(frozen=True)
class TrackJobResult:
    run_id: str
    run_dir: Path
    summary: dict[str, Any]


def build_detector(variant: str, settings: Settings) -> Detector:
    """RF-DETR als Ganzbild ("whole") oder auf Kacheln ("tiles")."""
    if variant not in VARIANTS:
        raise ValueError(f"Unbekannte Variante {variant!r}, erlaubt: {VARIANTS}")
    # Erst hier importieren: ohne installiertes rfdetr bleibt der Rest nutzbar.
    from matchstats.infrastructure.rfdetr_detector import RfDetrDetector

    detector: Detector = RfDetrDetector(settings.detector_model, settings.detect_min_score)
    if variant == "tiles":
        return TiledDetector(detector, settings.tile_size, settings.tile_overlap, settings.nms_iou)
    return detector


class _LazyDetector:
    """Baut den (teuren) Detektor erst beim ersten Bild: bei wiederverwendeten Erkennungen nie."""

    def __init__(self, variant: str, settings: Settings) -> None:
        self._variant = variant
        self._settings = settings
        self._inner: Detector | None = None

    def detect(self, image: np.ndarray) -> list[Detection]:
        if self._inner is None:
            self._inner = build_detector(self._variant, self._settings)
        return self._inner.detect(image)


def collect_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for name in ("matchstats", *_TRACKED_PACKAGES):
        try:
            versions[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            continue
    return versions


def run_track_job(
    library: Library,
    game: str,
    clip_id: str,
    variant: str,
    config: Path | None = None,
    run_id: str | None = None,
    render: bool = True,
) -> TrackJobResult:
    """Erkennen (oder wiederverwenden), tracken, darstellen. Ohne run_id: neuer Lauf."""
    if variant not in VARIANTS:
        raise ValueError(f"Unbekannte Variante {variant!r}, erlaubt: {VARIANTS}")
    clip = library.get_clip(game, clip_id)
    if run_id is None:
        settings = load_settings(config, profile_overrides=clip.settings)
        run_id = library.create_run(game, clip_id, asdict(settings)).id
    else:
        known = {r.id: r for r in library.list_runs(game, clip_id)}
        if run_id not in known:
            raise LibraryError(f"Lauf {run_id} existiert nicht (Spiel {game}, Clip {clip_id})")
        try:
            # die Parameter des Laufs bleiben gültig
            settings = Settings(**known[run_id].settings)
        except TypeError as err:
            raise ValueError(
                f"Lauf {run_id} enthält unbekannte oder fehlerhafte Einstellungen: {err}"
            ) from err

    run_dir = library.run_dir(game, clip_id, run_id)
    source = OpenCvFrameSource(library.clip_dir(game, clip_id) / Path(clip.source_file).name)
    store = FileStageStore(run_dir)
    versions = collect_versions()
    detector_name = f"rfdetr-{settings.detector_model}-{variant}"

    seconds: dict[str, float | None] = {"detection": None, "tracking": None, "render": None}
    start = time.perf_counter()
    doc, reused = detect_stage(
        source, _LazyDetector(variant, settings), detector_name, settings, store, versions
    )
    if not reused:
        seconds["detection"] = time.perf_counter() - start

    start = time.perf_counter()
    tracker = ByteTrackLikeTracker(settings, doc.fps)
    result = track_stage(doc, tracker, settings, store, versions)
    seconds["tracking"] = time.perf_counter() - start

    candidates = find_id_switch_candidates(
        result.tracks, doc.fps, doc.frame_size, doc.frame_count, settings
    )
    write_json_atomic(
        run_dir / SWITCH_FILE,
        {
            "schema_version": SWITCH_SCHEMA_VERSION,
            "note": "Kandidaten, keine bestätigten ID-Wechsel (siehe Spezifikation T4).",
            "candidates": [asdict(c) for c in candidates],
        },
    )

    if render:
        start = time.perf_counter()
        render_tracks(source, result, run_dir / "render", candidates)
        seconds["render"] = time.perf_counter() - start

    summary = {
        "schema_version": SUMMARY_SCHEMA_VERSION,
        **summarize_tracks(result),
        **summarize_id_switch_candidates(result, candidates),
        "stage_seconds": seconds,  # None = Stufe nicht gelaufen (z. B. Erkennung wiederverwendet)
        "detections_reused": reused,
    }
    write_json_atomic(run_dir / SUMMARY_FILE, summary)
    return TrackJobResult(run_id=run_id, run_dir=run_dir, summary=summary)
