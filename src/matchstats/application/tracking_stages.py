"""Stufen des Trackings: Erkennung (detect_stage) und Spurbildung (track_stage).

Beide kennen nur Ports (Videoquelle, Detektor, Speicher, Tracker), keine Bibliotheken.
"""

from collections.abc import Iterator
from dataclasses import asdict
from typing import Any, Protocol

import numpy as np

from matchstats.application.detector import Detector
from matchstats.application.tracker import Tracker
from matchstats.domain.result import RunResult
from matchstats.domain.settings import Settings
from matchstats.domain.tracking import DetectionsDoc, FrameDetections


class FrameSource(Protocol):
    fps: float
    frame_count: int
    frame_size: tuple[int, int]  # (Breite, Höhe)
    name: str  # Dateiname

    def frames(self, every: int) -> Iterator[tuple[int, np.ndarray]]:
        """Liefert (Index, RGB-Bild) für alle Indizes mit Index % every == 0, bildweise."""
        ...


class StageStore(Protocol):
    def load_detections(self) -> DetectionsDoc | None:
        """None, wenn keine (vollständige) Datei vorliegt."""
        ...

    def save_detections(self, doc: DetectionsDoc) -> None: ...

    def save_tracks(self, result: RunResult) -> None: ...


def _stage_params(detector_name: str, settings: Settings) -> dict[str, Any]:
    """Alles, was das Erkennungsergebnis bestimmt (dient als Cache-Schlüssel)."""
    return {
        "detector": detector_name,
        "detect_every": settings.detect_every,
        "detect_min_score": settings.detect_min_score,
        "detector_model": settings.detector_model,
        "tile_size": settings.tile_size,
        "tile_overlap": settings.tile_overlap,
        "nms_iou": settings.nms_iou,
    }


def _is_reusable(doc: DetectionsDoc, source: FrameSource, params: dict[str, Any]) -> bool:
    """Gleiche Parameter und dasselbe Video (Name, Bildanzahl, Bildgröße)."""
    return (
        doc.stage_params == params
        and doc.source == source.name
        and doc.frame_count == source.frame_count
        and tuple(doc.frame_size) == tuple(source.frame_size)
    )


def detect_stage(
    source: FrameSource,
    detector: Detector,
    detector_name: str,
    settings: Settings,
    store: StageStore,
    versions: dict[str, str],
) -> tuple[DetectionsDoc, bool]:
    """Erkennt auf jedem N-ten Bild. Liefert (Dokument, wiederverwendet?).

    Wiederverwendet wird nur, wenn die gespeicherten stage_params und das Video (source,
    frame_count, frame_size) gleich sind; dann wird weder
    das Video gelesen noch der Detektor aufgerufen. Gespeichert werden nur Erkennungen mit
    score >= detect_min_score.
    """
    params = _stage_params(detector_name, settings)
    existing = store.load_detections()
    if existing is not None and _is_reusable(existing, source, params):
        return existing, True

    frames: list[FrameDetections] = []
    for index, image in source.frames(settings.detect_every):
        kept = tuple(d for d in detector.detect(image) if d.score >= settings.detect_min_score)
        frames.append(FrameDetections(frame=index, detections=kept))
    doc = DetectionsDoc(
        source=source.name,
        detector=detector_name,
        fps=source.fps,
        frame_count=source.frame_count,
        frame_size=source.frame_size,
        stage_params=params,
        versions=versions,
        frames=tuple(frames),
    )
    store.save_detections(doc)
    return doc, False


def track_stage(
    doc: DetectionsDoc,
    tracker: Tracker,
    settings: Settings,
    store: StageStore,
    versions: dict[str, str],
) -> RunResult:
    """Bildet Spuren aus den Erkennungen. Läuft immer neu und speichert tracks.json."""
    tracks = tracker.track(doc.frames, doc.frame_count, doc.frame_size)
    result = RunResult(
        source=doc.source,
        settings=asdict(settings),
        tracks=tuple(tracks),
        fps=doc.fps,
        frame_count=doc.frame_count,
        versions=dict(versions),
    )
    store.save_tracks(result)
    return result
