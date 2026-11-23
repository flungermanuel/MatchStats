"""T4b: camera.json (Rundreise, null bei fehlgeschlagener Schätzung, schema_version)."""

import json

import pytest
from matchstats.domain.camera import CAMERA_SCHEMA_VERSION, CameraDoc, CameraMotion

from matchstats.infrastructure.stage_files import FileStageStore


def _doc() -> CameraDoc:
    return CameraDoc(
        source="clip.mp4",
        fps=25.0,
        frame_count=4,
        frame_size=(160, 90),
        stage_params={
            "camera_downscale": 0.5,
            "camera_min_quality": 0.3,
            "camera_max_features": 400,
        },
        versions={"opencv-python": "4.10"},
        motions=(
            CameraMotion(1, ((1.0, 0.0, 2.5), (0.0, 1.0, -1.0)), 0.9),
            CameraMotion(2, None, None),
            CameraMotion(3, ((1.02, 0.0, -3.0), (0.0, 1.02, 0.5)), 0.7),
        ),
    )


def test_camera_schema_version_is_1():
    assert CAMERA_SCHEMA_VERSION == 1


def test_camera_json_keeps_failed_estimate_as_null(tmp_path):
    store = FileStageStore(tmp_path)
    store.save_camera(_doc())

    raw = json.loads((tmp_path / "camera.json").read_text(encoding="utf-8"))
    assert raw["schema_version"] == 1
    assert raw["frames"][1] == {"frame": 2, "matrix": None, "quality": None}
    loaded = store.load_camera()
    assert loaded == _doc()
    assert loaded.motions[1].matrix is None  # nicht Einheitsmatrix


def test_camera_json_stores_matrices_as_nested_lists(tmp_path):
    FileStageStore(tmp_path).save_camera(_doc())

    raw = json.loads((tmp_path / "camera.json").read_text(encoding="utf-8"))
    assert raw["frames"][0]["matrix"] == [[1.0, 0.0, 2.5], [0.0, 1.0, -1.0]]
    assert raw["frame_size"] == [160, 90]


def test_load_camera_returns_none_when_no_file_exists(tmp_path):
    assert FileStageStore(tmp_path).load_camera() is None


def test_camera_json_rejects_unknown_schema_version(tmp_path):
    FileStageStore(tmp_path).save_camera(_doc())
    path = tmp_path / "camera.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["schema_version"] = 9
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError) as error:
        FileStageStore(tmp_path).load_camera()

    message = str(error.value)
    assert "camera.json" in message
    assert "9" in message and "1" in message


def test_camera_doc_gives_a_path_that_knows_its_motions():
    path = _doc().path()

    assert path.transform(0, 1) == ((1.0, 0.0, 2.5), (0.0, 1.0, -1.0))
    assert path.transform(0, 3) is None  # Bild 2 ist unbekannt
