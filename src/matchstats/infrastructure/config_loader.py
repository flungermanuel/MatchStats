"""Lädt Parameter: Standard (default.toml) -> Datei -> Aufnahme-Profil -> Clip -> Aufruf."""

import tomllib
from collections.abc import Mapping
from dataclasses import fields
from pathlib import Path
from typing import Any

from matchstats.domain.settings import Settings

DEFAULT_CONFIG = Path(__file__).with_name("default.toml")


def load_settings(
    path: Path | None = None,
    camera_motion: str | None = None,
    profile_overrides: Mapping[str, Any] | None = None,
    overrides: Mapping[str, Any] | None = None,
) -> Settings:
    """Schichtet die Parameter; spätere Schichten überschreiben frühere.

    Reihenfolge: Standard, optionale eigene TOML-Datei (`path`), Aufnahme-Profil
    (`camera_motion`, None = "unbekannt"; Werte aus [camera_motion_presets]), Clip-Einstellungen
    (`profile_overrides`), Aufruf-Argumente. Unbekannte Schlüssel in einer Schicht werden mit
    ihrem Namen abgelehnt (ValueError).
    """
    values = tomllib.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    presets = values.pop("camera_motion_presets")  # keine Einstellung, nur Profil-Daten
    name = camera_motion or "unbekannt"
    if name not in presets:
        raise ValueError(
            f"Unbekanntes Aufnahme-Profil camera_motion {name!r}, erlaubt: {list(presets)}"
        )
    layers: list[tuple[str, Mapping[str, Any]]] = []
    if path is not None:
        layers.append((str(path), tomllib.loads(Path(path).read_text(encoding="utf-8"))))
    layers.append((f"Aufnahme-Profil {name}", presets[name]))
    layers.append(("Profil", profile_overrides or {}))
    layers.append(("Aufruf", overrides or {}))

    known = {f.name for f in fields(Settings)}
    for source, layer in layers:
        unknown = sorted(set(layer) - known)
        if unknown:
            raise ValueError(f"Unbekannter Parameter {', '.join(unknown)} ({source})")
        values.update(layer)
    return Settings(**values)
