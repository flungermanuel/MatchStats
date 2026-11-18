"""Schnittstelle (Port) der Bibliothek: Spiele, Clips und Läufe verwalten."""

from pathlib import Path
from typing import Any, Protocol

from matchstats.domain.library import Clip, Match, RecordingProfile, RunInfo


class LibraryError(ValueError):
    """Ein Bibliotheksvorgang ist fehlgeschlagen (Meldung nennt ID bzw. Dateiname)."""


class Library(Protocol):
    def add_match(self, match: Match) -> None: ...

    def get_match(self, match_id: str) -> Match: ...

    def import_clip(
        self,
        match_id: str,
        video_path: Path,
        clip_id: str,
        half: int | None,
        profile: RecordingProfile,
        settings: dict[str, Any],
    ) -> Clip: ...

    def get_clip(self, match_id: str, clip_id: str) -> Clip: ...

    def list_clips(self, match_id: str, half: int | None = None) -> list[Clip]: ...

    def create_run(self, match_id: str, clip_id: str, settings: dict[str, Any]) -> RunInfo: ...

    def list_runs(self, match_id: str, clip_id: str) -> list[RunInfo]: ...

    def clip_dir(self, match_id: str, clip_id: str) -> Path: ...

    def run_dir(self, match_id: str, clip_id: str, run_id: str) -> Path: ...
