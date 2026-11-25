"""T5b1: teams.json (Rundreise, null bleibt null, schema_version, Pflichtfelder)."""

import json

import pytest

from matchstats.domain.teams import TEAMS_SCHEMA_VERSION, UNKNOWN, TeamsDoc, TrackTeam
from matchstats.infrastructure.stage_files import TEAMS_FILE, FileStageStore


def _doc() -> TeamsDoc:
    return TeamsDoc(
        source="clip.mp4",
        fps=25.0,
        frame_count=100,
        frame_size=(320, 180),
        stage_params={"team_samples_per_track": 8, "team_grass_hue_range": [35, 85]},
        tracks_fingerprint="ab" * 32,
        versions={"numpy": "2.0"},
        note="team_a ist willkürlich",
        tracks=(
            TrackTeam(
                1,
                "team_a",
                0.25,
                4,
                {"team_a": 3, "team_b": 1, "goalkeeper": 0, "referee": 0, UNKNOWN: 0},
            ),
            TrackTeam(
                2,
                None,
                None,
                0,
                {"team_a": 0, "team_b": 0, "goalkeeper": 0, "referee": 0, UNKNOWN: 0},
            ),
        ),
    )


def _write(tmp_path):
    FileStageStore(tmp_path).save_teams(_doc())
    return tmp_path / "teams.json"


def _rewrite(path, change):
    raw = json.loads(path.read_text(encoding="utf-8"))
    change(raw)
    path.write_text(json.dumps(raw), encoding="utf-8")


def test_teams_file_name_and_schema_version():
    assert TEAMS_FILE == "teams.json"
    assert TEAMS_SCHEMA_VERSION == 1


def test_teams_json_roundtrip_returns_equal_document(tmp_path):
    store = FileStageStore(tmp_path)
    store.save_teams(_doc())

    loaded = store.load_teams()

    assert loaded == _doc()
    assert isinstance(loaded.frame_size, tuple)
    assert isinstance(loaded.tracks, tuple)


def test_teams_json_has_required_fields_and_all_five_vote_keys(tmp_path):
    raw = json.loads(_write(tmp_path).read_text(encoding="utf-8"))

    assert raw["schema_version"] == 1
    for key in (
        "source",
        "fps",
        "frame_count",
        "frame_size",
        "stage_params",
        "tracks_fingerprint",
        "versions",
        "note",
        "tracks",
    ):
        assert key in raw
    for entry in raw["tracks"]:
        assert set(entry) == {"id", "label", "uncertainty", "samples", "votes"}
        assert set(entry["votes"]) == {"team_a", "team_b", "goalkeeper", "referee", "unbekannt"}


def test_teams_json_keeps_missing_label_and_uncertainty_as_null(tmp_path):
    raw = json.loads(_write(tmp_path).read_text(encoding="utf-8"))

    assert raw["tracks"][1]["label"] is None
    assert raw["tracks"][1]["uncertainty"] is None
    loaded = FileStageStore(tmp_path).load_teams()
    assert loaded.tracks[1].label is None
    assert loaded.tracks[1].uncertainty is None


def test_missing_teams_file_loads_as_none(tmp_path):
    assert FileStageStore(tmp_path).load_teams() is None


def test_truncated_teams_file_loads_as_none(tmp_path):
    path = _write(tmp_path)
    path.write_text(path.read_text(encoding="utf-8")[:80], encoding="utf-8")

    assert FileStageStore(tmp_path).load_teams() is None


def test_teams_file_with_missing_required_key_loads_as_none(tmp_path):
    path = _write(tmp_path)
    _rewrite(path, lambda raw: raw.pop("tracks_fingerprint"))

    assert FileStageStore(tmp_path).load_teams() is None


def test_teams_file_with_wrong_version_raises_clear_error(tmp_path):
    path = _write(tmp_path)
    _rewrite(path, lambda raw: raw.update(schema_version=99))

    with pytest.raises(ValueError, match="teams.json") as error:
        FileStageStore(tmp_path).load_teams()
    assert "schema_version" in str(error.value)


def test_teams_file_without_version_raises_error(tmp_path):
    path = _write(tmp_path)
    _rewrite(path, lambda raw: raw.pop("schema_version"))

    with pytest.raises(ValueError, match="schema_version"):
        FileStageStore(tmp_path).load_teams()


def test_saving_teams_leaves_no_temporary_file(tmp_path):
    _write(tmp_path)

    assert sorted(p.name for p in tmp_path.iterdir()) == ["teams.json"]
