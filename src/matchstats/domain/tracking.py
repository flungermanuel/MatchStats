"""Datentypen des Trackings: Erkennungen je Bild (detections.json) und Spuren (tracks.json)."""

from dataclasses import dataclass
from typing import Any

from matchstats.domain.detection import Detection

# Wird erhöht, sobald sich das Format von detections.json ändert.
DETECTIONS_SCHEMA_VERSION = 1


@dataclass(frozen=True)
class FrameDetections:
    frame: int  # Bildindex im Clip (0-basiert)
    detections: tuple[Detection, ...]


@dataclass(frozen=True)
class TrackPoint:
    frame: int
    x: float  # Box in Pixeln, x/y = linke obere Ecke
    y: float
    w: float
    h: float
    visible: bool  # True = vom Detektor gesehen, False = vom Tracker überbrückt
    score: float | None  # Detektor-Score; None, wenn nicht gesehen
    uncertainty: float | None = None  # Platzhalter für T6, in T4 immer None


@dataclass(frozen=True)
class Track:
    id: int
    # nach frame aufsteigend, ohne Lücken zwischen erstem und letztem Punkt
    points: tuple[TrackPoint, ...]


@dataclass(frozen=True)
class DetectionsDoc:
    """Inhalt von detections.json."""

    source: str  # Dateiname des Videos
    detector: str  # z. B. "rfdetr-small-whole"
    fps: float
    frame_count: int
    frame_size: tuple[int, int]  # (Breite, Höhe)
    stage_params: dict[str, Any]  # Parameter, die das Ergebnis bestimmen (Cache-Schlüssel)
    versions: dict[str, str]  # Bibliotheks- und Modellversionen
    frames: tuple[FrameDetections, ...]
    schema_version: int = DETECTIONS_SCHEMA_VERSION
