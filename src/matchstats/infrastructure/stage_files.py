"""Zwischenergebnisse eines Laufs als Dateien im Lauf-Ordner (detections, camera, tracks)."""

import json
from dataclasses import asdict
from pathlib import Path

from matchstats.domain.camera import CAMERA_SCHEMA_VERSION, CameraDoc, CameraMotion
from matchstats.domain.detection import Detection
from matchstats.domain.result import RunResult
from matchstats.domain.teams import TEAMS_SCHEMA_VERSION, TeamsDoc, TrackTeam
from matchstats.domain.tracking import DETECTIONS_SCHEMA_VERSION, DetectionsDoc, FrameDetections
from matchstats.infrastructure.json_io import write_json_atomic
from matchstats.infrastructure.result_store import save_result

DETECTIONS_FILE = "detections.json"
CAMERA_FILE = "camera.json"
TEAMS_FILE = "teams.json"


class FileStageStore:
    def __init__(self, run_dir: Path) -> None:
        self._dir = Path(run_dir)

    def load_detections(self) -> DetectionsDoc | None:
        """None, wenn die Datei fehlt oder unvollständig ist; falsche Version -> ValueError."""
        path = self._dir / DETECTIONS_FILE
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return None  # abgeschnitten: neu berechnen
        version = data.get("schema_version") if isinstance(data, dict) else None
        if version != DETECTIONS_SCHEMA_VERSION:
            raise ValueError(
                f"{DETECTIONS_FILE}: schema_version {version!r} wird nicht unterstützt, "
                f"erwartet {DETECTIONS_SCHEMA_VERSION}"
            )
        try:
            return DetectionsDoc(
                source=data["source"],
                detector=data["detector"],
                fps=data["fps"],
                frame_count=data["frame_count"],
                frame_size=(data["frame_size"][0], data["frame_size"][1]),
                stage_params=data["stage_params"],
                versions=data["versions"],
                frames=tuple(
                    FrameDetections(f["frame"], tuple(Detection(**d) for d in f["detections"]))
                    for f in data["frames"]
                ),
            )
        except (KeyError, TypeError, IndexError):
            return None

    def save_detections(self, doc: DetectionsDoc) -> None:
        write_json_atomic(self._dir / DETECTIONS_FILE, asdict(doc))

    def load_camera(self) -> CameraDoc | None:
        """None, wenn die Datei fehlt oder unvollständig ist; falsche Version -> ValueError."""
        path = self._dir / CAMERA_FILE
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return None  # abgeschnitten: neu berechnen
        version = data.get("schema_version") if isinstance(data, dict) else None
        if version != CAMERA_SCHEMA_VERSION:
            raise ValueError(
                f"{CAMERA_FILE}: schema_version {version!r} wird nicht unterstützt, "
                f"erwartet {CAMERA_SCHEMA_VERSION}"
            )
        try:
            return CameraDoc(
                source=data["source"],
                fps=data["fps"],
                frame_count=data["frame_count"],
                frame_size=(data["frame_size"][0], data["frame_size"][1]),
                stage_params=data["stage_params"],
                versions=data["versions"],
                motions=tuple(_motion_from_json(f) for f in data["frames"]),
            )
        except (KeyError, TypeError, IndexError):
            return None

    def save_camera(self, doc: CameraDoc) -> None:
        data = asdict(doc)
        data["frames"] = data.pop("motions")  # Matrizen werden zu verschachtelten Listen
        write_json_atomic(self._dir / CAMERA_FILE, data)

    def load_teams(self) -> TeamsDoc | None:
        """None, wenn die Datei fehlt oder unvollständig ist; falsche Version -> ValueError."""
        path = self._dir / TEAMS_FILE
        if not path.is_file():
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except ValueError:
            return None  # abgeschnitten: neu berechnen
        version = data.get("schema_version") if isinstance(data, dict) else None
        if version != TEAMS_SCHEMA_VERSION:
            raise ValueError(
                f"{TEAMS_FILE}: schema_version {version!r} wird nicht unterstützt, "
                f"erwartet {TEAMS_SCHEMA_VERSION}"
            )
        try:
            return TeamsDoc(
                source=data["source"],
                fps=data["fps"],
                frame_count=data["frame_count"],
                frame_size=(data["frame_size"][0], data["frame_size"][1]),
                stage_params=data["stage_params"],
                tracks_fingerprint=data["tracks_fingerprint"],
                versions=data["versions"],
                note=data["note"],
                tracks=tuple(
                    TrackTeam(
                        id=t["id"],
                        label=t["label"],
                        uncertainty=t["uncertainty"],
                        samples=t["samples"],
                        votes=t["votes"],
                    )
                    for t in data["tracks"]
                ),
            )
        except (KeyError, TypeError, IndexError):
            return None

    def save_teams(self, doc: TeamsDoc) -> None:
        write_json_atomic(self._dir / TEAMS_FILE, asdict(doc))

    def save_tracks(self, result: RunResult) -> None:
        save_result(result, self._dir)


def _motion_from_json(entry: dict) -> CameraMotion:
    matrix = entry["matrix"]
    return CameraMotion(
        frame=entry["frame"],
        matrix=None if matrix is None else (tuple(matrix[0]), tuple(matrix[1])),
        quality=entry["quality"],
    )
