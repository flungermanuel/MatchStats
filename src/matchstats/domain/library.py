"""Datentypen der Bibliothek: Spiel, Clip (mit Aufnahme-Profil) und Lauf. Rein, keine I/O."""

from dataclasses import dataclass, field
from typing import Any

# Version des Dateiformats (match.json, clip.json, run.json). Bei Formatänderung erhöhen.
SCHEMA_VERSION = 1

# Bekannte Werte des Aufnahme-Profils; unbekannt wird als None gespeichert, nicht geraten.
ANGLES: tuple[str, ...] = ("tribuene_hoch", "seitenlinie", "ecke", "hinter_tor", "sonstige")
CAMERA_MOTIONS: tuple[str, ...] = ("fest", "schwenkt", "schwenkt_und_zoomt")


@dataclass(frozen=True)
class Match:
    id: str
    name: str
    date: str | None  # ISO-Datum, z. B. "2026-11-15"
    notes: str


@dataclass(frozen=True)
class RecordingProfile:
    angle: str | None
    camera_motion: str | None
    notes: str

    def __post_init__(self) -> None:
        if self.angle is not None and self.angle not in ANGLES:
            raise ValueError(f"angle {self.angle!r} unbekannt, erlaubt: {ANGLES} oder None")
        if self.camera_motion is not None and self.camera_motion not in CAMERA_MOTIONS:
            raise ValueError(
                f"camera_motion {self.camera_motion!r} unbekannt, "
                f"erlaubt: {CAMERA_MOTIONS} oder None"
            )


@dataclass(frozen=True)
class Clip:
    id: str
    match_id: str
    half: int | None  # 1, 2 oder None (unbekannt)
    source_file: str  # relativ zum Bibliotheksordner, mit "/"
    fps: float
    width: int
    height: int
    duration_s: float
    profile: RecordingProfile
    # Profil-Überschreibungen der Parameter (nur die Schlüssel, die vom Standard abweichen).
    settings: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.half, bool) or self.half not in (1, 2, None):
            raise ValueError(f"half muss 1, 2 oder None sein, nicht {self.half!r}")
        if self.fps <= 0:
            raise ValueError(f"fps muss größer 0 sein, nicht {self.fps!r}")
        if self.width <= 0:
            raise ValueError(f"width muss größer 0 sein, nicht {self.width!r}")
        if self.height <= 0:
            raise ValueError(f"height muss größer 0 sein, nicht {self.height!r}")
        if self.duration_s < 0:
            raise ValueError(f"duration_s darf nicht negativ sein, nicht {self.duration_s!r}")


@dataclass(frozen=True)
class RunInfo:
    id: str
    created: str  # ISO-Zeitstempel
    clip_id: str
    settings: dict[str, Any]  # aufgelöste Parameter: Standard -> Profil -> Aufruf
