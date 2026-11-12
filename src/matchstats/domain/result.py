"""Ergebnis eines Laufs (das, was als tracks.json gespeichert wird)."""

from dataclasses import dataclass, field

# Wird erhöht, sobald sich das Format der Spurdatei ändert.
SCHEMA_VERSION = 1


@dataclass(frozen=True)
class RunResult:
    source: str  # nur der Dateiname des Videos, kein Pfad
    settings: dict
    # In T1 leer. Ab T4/T6 kommen hier Spuren mit Sichtbarkeit und Unsicherheit hinein.
    tracks: list = field(default_factory=list)
    schema_version: int = SCHEMA_VERSION
