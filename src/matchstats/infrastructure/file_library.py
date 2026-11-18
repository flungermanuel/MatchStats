"""Bibliothek als Ordnerstruktur unter <root>.

Aufbau: <spiel>/match.json, <spiel>/<clip>/clip.json + clip.mp4, <clip>/runs/<lauf>/run.json.

Jede JSON-Datei trägt eine schema_version. Pfade in den Dateien sind relativ zu <root> und
verwenden "/". Das Original-Video wird nur gelesen (Import kopiert).
"""

import json
import re
import shutil
from dataclasses import asdict
from datetime import datetime
from pathlib import Path
from typing import Any

from matchstats.application.library import LibraryError
from matchstats.domain.library import SCHEMA_VERSION, Clip, Match, RecordingProfile, RunInfo
from matchstats.infrastructure.frame_sampler import FrameSamplingError, probe_video

VIDEO_NAME = "clip.mp4"
_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]*")


def _check_id(kind: str, value: str) -> None:
    """IDs werden zu Ordnernamen: nur einfache Zeichen, keine Pfadteile."""
    if not isinstance(value, str) or _ID_PATTERN.fullmatch(value) is None:
        raise LibraryError(
            f"Ungültige {kind}-ID {value!r}: erlaubt sind Buchstaben, Ziffern, _ und -"
        )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    """Schreibt erst in eine Hilfsdatei und ersetzt dann, damit nie halbe Dateien liegen."""
    data = {"schema_version": SCHEMA_VERSION, **payload}
    tmp = path.with_name(path.name + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    tmp.replace(path)


def _read_json(path: Path) -> dict[str, Any]:
    """Liest eine Bibliotheksdatei und prüft die schema_version."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        raise LibraryError(f"{path.name} ist nicht lesbar ({path.parent.name}): {err}") from err
    if not isinstance(data, dict):
        raise LibraryError(f"{path.name} ({path.parent.name}): Objekt erwartet")
    version = data.get("schema_version")
    if isinstance(version, bool) or version != SCHEMA_VERSION:
        raise LibraryError(
            f"{path.name} ({path.parent.name}): schema_version {version!r} wird nicht "
            f"unterstützt, erwartet {SCHEMA_VERSION}"
        )
    return data


def _clip_from_json(path: Path, data: dict[str, Any]) -> Clip:
    try:
        return Clip(
            id=data["id"],
            match_id=data["match_id"],
            half=data["half"],
            source_file=data["source_file"],
            fps=data["fps"],
            width=data["width"],
            height=data["height"],
            duration_s=data["duration_s"],
            profile=RecordingProfile(**data["profile"]),
            settings=dict(data["settings"]),
        )
    except (KeyError, TypeError, ValueError) as err:
        raise LibraryError(f"{path.name} ({path.parent.name}) ist ungültig: {err}") from err


class FileLibrary:
    def __init__(self, root: Path) -> None:
        self.root = Path(root)

    # --- Pfade ---

    def _match_dir(self, match_id: str) -> Path:
        _check_id("Spiel", match_id)
        return self.root / match_id

    def clip_dir(self, match_id: str, clip_id: str) -> Path:
        _check_id("Clip", clip_id)
        return self._match_dir(match_id) / clip_id

    def run_dir(self, match_id: str, clip_id: str, run_id: str) -> Path:
        _check_id("Lauf", run_id)
        return self.clip_dir(match_id, clip_id) / "runs" / run_id

    # --- Spiele ---

    def add_match(self, match: Match) -> None:
        folder = self._match_dir(match.id)
        if (folder / "match.json").exists():
            raise LibraryError(f"Spiel {match.id} existiert bereits")
        folder.mkdir(parents=True, exist_ok=True)
        _write_json(folder / "match.json", asdict(match))

    def get_match(self, match_id: str) -> Match:
        path = self._match_dir(match_id) / "match.json"
        if not path.is_file():
            raise LibraryError(f"Spiel {match_id} nicht gefunden")
        data = _read_json(path)
        try:
            return Match(id=data["id"], name=data["name"], date=data["date"], notes=data["notes"])
        except KeyError as err:
            raise LibraryError(f"match.json ({match_id}) ist ungültig: {err}") from err

    # --- Clips ---

    def import_clip(
        self,
        match_id: str,
        video_path: Path,
        clip_id: str,
        half: int | None,
        profile: RecordingProfile,
        settings: dict[str, Any],
    ) -> Clip:
        self.get_match(match_id)  # wirft, wenn das Spiel fehlt
        video_path = Path(video_path)
        if not video_path.is_file():
            raise LibraryError(f"Video nicht gefunden: {video_path.name}")
        folder = self.clip_dir(match_id, clip_id)
        if folder.exists():
            raise LibraryError(f"Clip {clip_id} existiert bereits in Spiel {match_id}")
        try:
            info = probe_video(video_path)  # vor dem Anlegen: ein Fehlschlag hinterlässt nichts
        except FrameSamplingError as err:
            raise LibraryError(f"{video_path.name} ist kein lesbares Video: {err}") from err

        try:
            clip = Clip(
                id=clip_id, match_id=match_id, half=half,
                source_file=f"{match_id}/{clip_id}/{VIDEO_NAME}",
                fps=info.fps, width=info.width, height=info.height,
                duration_s=info.duration_s, profile=profile, settings=dict(settings),
            )  # fmt: skip
        except ValueError as err:
            raise LibraryError(f"Clip {clip_id}: {err}") from err

        try:
            folder.mkdir(parents=True)
            shutil.copy2(video_path, folder / VIDEO_NAME)
            _write_json(folder / "clip.json", asdict(clip))
        except BaseException:
            shutil.rmtree(folder, ignore_errors=True)  # kein halber Clip-Ordner
            raise
        return clip

    def get_clip(self, match_id: str, clip_id: str) -> Clip:
        path = self.clip_dir(match_id, clip_id) / "clip.json"
        if not path.is_file():
            raise LibraryError(f"Clip {clip_id} in Spiel {match_id} nicht gefunden")
        return _clip_from_json(path, _read_json(path))

    def list_clips(self, match_id: str, half: int | None = None) -> list[Clip]:
        self.get_match(match_id)
        clips = [
            self.get_clip(match_id, path.parent.name)
            for path in sorted(self._match_dir(match_id).glob("*/clip.json"))
        ]
        return [c for c in clips if half is None or c.half == half]

    # --- Läufe ---

    def create_run(self, match_id: str, clip_id: str, settings: dict[str, Any]) -> RunInfo:
        self.get_clip(match_id, clip_id)
        runs = self.clip_dir(match_id, clip_id) / "runs"
        numbers = (
            [int(p.name[4:]) for p in runs.glob("run-*") if p.name[4:].isdigit()]
            if runs.is_dir()
            else []
        )
        run = RunInfo(
            id=f"run-{max(numbers, default=0) + 1:03d}",
            created=datetime.now().isoformat(timespec="seconds"),
            clip_id=clip_id,
            settings=dict(settings),
        )
        folder = self.run_dir(match_id, clip_id, run.id)
        folder.mkdir(parents=True)  # bestehende Läufe werden nie überschrieben
        _write_json(folder / "run.json", asdict(run))
        return run

    def list_runs(self, match_id: str, clip_id: str) -> list[RunInfo]:
        self.get_clip(match_id, clip_id)
        runs: list[RunInfo] = []
        for path in sorted((self.clip_dir(match_id, clip_id) / "runs").glob("*/run.json")):
            data = _read_json(path)
            try:
                runs.append(
                    RunInfo(
                        id=data["id"], created=data["created"],
                        clip_id=data["clip_id"], settings=dict(data["settings"]),
                    )
                )  # fmt: skip
            except (KeyError, TypeError) as err:
                raise LibraryError(f"run.json ({path.parent.name}) ist ungültig: {err}") from err
        return runs
