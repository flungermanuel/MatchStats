"""Lädt Parameter aus einer TOML-Datei (Standard: default.toml im Paket)."""

import tomllib
from pathlib import Path

from matchstats.domain.settings import Settings

DEFAULT_CONFIG = Path(__file__).with_name("default.toml")


def load_settings(path: Path | None = None) -> Settings:
    """Standardwerte laden und, falls angegeben, mit einer eigenen Datei überschreiben."""
    values = tomllib.loads(DEFAULT_CONFIG.read_text(encoding="utf-8"))
    if path is not None:
        values.update(tomllib.loads(Path(path).read_text(encoding="utf-8")))
    return Settings(**values)
