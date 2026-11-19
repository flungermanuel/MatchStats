"""T4: detections.json und tracks.json (Roundtrip, schema_version, null, keine halben Dateien)."""

import json

import pytest
from matchstats.domain.tracking import DetectionsDoc, FrameDetections, Track, TrackPoint
from matchstats.infrastructure.stage_files import FileStageStore

from matchstats.domain.detection import Detection
from matchstats.domain.result import SCHEMA_VERSION, RunResult
from matchstats.infrastructure.result_store import load_result, save_result


def _doc() -> DetectionsDoc:
    return DetectionsDoc(
        source="clip.mp4",
        detector="rfdetr-small-whole",
        fps=25.0,
        frame_count=15,
        frame_size=(160, 90),
        stage_params={"detector": "rfdetr-small-whole", "detect_every": 5, "tile_size": 640},
        versions={"rfdetr": "1.2.3"},
        frames=(
            FrameDetections(0, (Detection(10.0, 20.0, 20.0, 50.0, 0.9),)),
            FrameDetections(5, ()),
            FrameDetections(10, (Detection(12.5, 20.0, 20.0, 50.0, 0.4),)),
        ),
    )


def _result() -> RunResult:
    points = (
        TrackPoint(0, 10.0, 20.0, 20.0, 50.0, True, 0.9),
        TrackPoint(1, 10.5, 20.0, 20.0, 50.0, False, None),
        TrackPoint(2, 11.0, 20.0, 20.0, 50.0, True, 0.7),
    )
    return RunResult(
        source="clip.mp4",
        settings={"detect_every": 5},
        tracks=(Track(id=1, points=points),),
        fps=25.0,
        frame_count=15,
        versions={"rfdetr": "1.2.3"},
    )


# --- detections.json ---


def test_detections_survive_a_save_and_load_roundtrip(tmp_path):
    store = FileStageStore(tmp_path)
    store.save_detections(_doc())

    assert store.load_detections() == _doc()


def test_detections_file_is_written_as_detections_json_with_schema_version_1(tmp_path):
    FileStageStore(tmp_path).save_detections(_doc())

    data = json.loads((tmp_path / "detections.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == 1


def test_load_detections_returns_none_when_no_file_exists(tmp_path):
    assert FileStageStore(tmp_path).load_detections() is None


def test_load_detections_ignores_a_leftover_temp_file(tmp_path):
    (tmp_path / "detections.json.tmp").write_text('{"schema_version": 1', encoding="utf-8")

    assert FileStageStore(tmp_path).load_detections() is None


def test_saving_detections_leaves_no_temp_file_behind(tmp_path):
    FileStageStore(tmp_path).save_detections(_doc())

    assert [p.name for p in tmp_path.iterdir()] == ["detections.json"]


def test_load_detections_returns_none_for_an_incomplete_file(tmp_path):
    (tmp_path / "detections.json").write_text('{"schema_version": 1, "frames": [', encoding="utf-8")

    assert FileStageStore(tmp_path).load_detections() is None


def test_detections_with_wrong_schema_version_are_rejected_with_clear_message(tmp_path):
    FileStageStore(tmp_path).save_detections(_doc())
    path = tmp_path / "detections.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["schema_version"] = 7
    path.write_text(json.dumps(data), encoding="utf-8")

    with pytest.raises(ValueError) as error:
        FileStageStore(tmp_path).load_detections()

    message = str(error.value)
    assert "detections.json" in message
    assert "7" in message and "1" in message


# --- tracks.json ---


def test_tracks_result_has_schema_version_2():
    assert SCHEMA_VERSION == 2
    assert _result().schema_version == 2


def test_tracks_survive_a_save_and_load_roundtrip(tmp_path):
    path = save_result(_result(), tmp_path)

    assert path.name == "tracks.json"
    assert load_result(path) == _result()


def test_none_values_stay_null_in_the_file_and_none_after_loading(tmp_path):
    path = save_result(_result(), tmp_path)

    raw = json.loads(path.read_text(encoding="utf-8"))
    points = raw["tracks"][0]["points"]
    assert points[1]["score"] is None
    assert all(p["uncertainty"] is None for p in points)
    loaded = load_result(path)
    assert loaded.tracks[0].points[1].score is None
    assert loaded.tracks[0].points[1].visible is False
    assert loaded.tracks[0].points[0].uncertainty is None


def test_missing_fps_and_frame_count_stay_none_and_not_zero(tmp_path):
    empty = RunResult(source="clip.mp4", settings={})

    loaded = load_result(save_result(empty, tmp_path))

    assert loaded.fps is None
    assert loaded.frame_count is None
    assert loaded.tracks == ()


def test_tracks_file_of_version_1_is_rejected_with_clear_message(tmp_path):
    path = tmp_path / "tracks.json"
    path.write_text(
        json.dumps({"schema_version": 1, "source": "clip.mp4", "config": {}, "tracks": []}),
        encoding="utf-8",
    )

    with pytest.raises(ValueError) as error:
        load_result(path)

    message = str(error.value)
    assert "tracks.json" in message
    assert "1" in message and "2" in message


def test_stage_store_saves_tracks_as_tracks_json_in_the_run_folder(tmp_path):
    FileStageStore(tmp_path).save_tracks(_result())

    assert load_result(tmp_path / "tracks.json") == _result()
