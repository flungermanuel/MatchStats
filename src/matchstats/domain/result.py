"""Ergebnis eines Laufs (das, was als tracks.json gespeichert wird)."""

from dataclasses import dataclass, field

from matchstats.domain.tracking import Track

# Wird erhöht, sobald sich das Format der Spurdatei ändert.
SCHEMA_VERSION = 2


@dataclass(frozen=True)
class RunResult:
    source: str  # nur der Dateiname des Videos, kein Pfad
    settings: dict
    tracks: tuple[Track, ...] = ()
    # Unbekannt bleibt None (nicht 0), z. B. beim leeren Ergebnis von `run`.
    fps: float | None = None
    frame_count: int | None = None
    versions: dict[str, str] = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION
