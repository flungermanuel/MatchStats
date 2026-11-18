"""T3b AK 1 und Regeln: Spiel -> Clip -> Lauf als Ordnerstruktur (FileLibrary)."""

import hashlib
import json
from dataclasses import asdict

import pytest
from matchstats.application.library import LibraryError
from matchstats.domain.library import SCHEMA_VERSION, Match, RecordingProfile
from matchstats.infrastructure.file_library import FileLibrary

from conftest import requires_ffmpeg
from matchstats.infrastructure.config_loader import load_settings

NO_PROFILE = RecordingProfile(angle=None, camera_motion=None, notes="")
STAND = RecordingProfile(angle="tribuene_hoch", camera_motion="fest", notes="Stativ")
CORNER = RecordingProfile(angle="ecke", camera_motion="schwenkt", notes="")


@pytest.fixture
def root(tmp_path):
    return tmp_path / "library"


@pytest.fixture
def library(root):
    lib = FileLibrary(root)
    lib.add_match(Match(id="spiel-001", name="Testspiel", date="2026-11-15", notes=""))
    return lib


def sha256(path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# --- Regel 1: Spiel anlegen ---


def test_match_can_be_added_and_found_again(library):
    match = library.get_match("spiel-001")

    assert (match.name, match.date) == ("Testspiel", "2026-11-15")


def test_match_survives_reopening_the_library(root, library):
    assert FileLibrary(root).get_match("spiel-001").name == "Testspiel"


def test_duplicate_match_id_is_rejected_and_first_match_stays(library):
    with pytest.raises(LibraryError, match="spiel-001"):
        library.add_match(Match(id="spiel-001", name="Anderes", date=None, notes=""))

    assert library.get_match("spiel-001").name == "Testspiel"


def test_unknown_match_is_reported_with_its_id(library):
    with pytest.raises(LibraryError, match="spiel-999"):
        library.get_match("spiel-999")


# --- Regel 2: Clip importieren, Fehlerfälle ---


@requires_ffmpeg
def test_clip_can_be_imported_and_found_again(library, make_clip):
    library.import_clip("spiel-001", make_clip("quelle.mp4"), "clip1", 1, STAND, {})

    clip = library.get_clip("spiel-001", "clip1")
    assert (clip.id, clip.match_id, clip.half) == ("clip1", "spiel-001", 1)
    assert clip.profile == STAND
    assert (library.clip_dir("spiel-001", "clip1") / "clip.mp4").is_file()


@requires_ffmpeg
def test_import_into_unknown_match_is_rejected_with_match_id(library, make_clip):
    with pytest.raises(LibraryError, match="spiel-999"):
        library.import_clip("spiel-999", make_clip(), "clip1", 1, NO_PROFILE, {})


def test_import_of_missing_file_is_rejected_with_file_name(library, tmp_path):
    missing = tmp_path / "gibt_es_nicht.mp4"

    with pytest.raises(LibraryError, match="gibt_es_nicht.mp4"):
        library.import_clip("spiel-001", missing, "clip1", 1, NO_PROFILE, {})

    assert library.list_clips("spiel-001") == []


@requires_ffmpeg
def test_import_of_non_video_file_is_rejected_and_leaves_no_clip(library, tmp_path):
    fake = tmp_path / "kein_video.mp4"
    fake.write_text("das ist kein Video", encoding="utf-8")

    with pytest.raises(LibraryError, match="kein_video.mp4"):
        library.import_clip("spiel-001", fake, "clip1", 1, NO_PROFILE, {})

    assert library.list_clips("spiel-001") == []
    assert not library.clip_dir("spiel-001", "clip1").exists()


# --- Regel 3: Metadaten aus ffprobe ---


@requires_ffmpeg
def test_import_records_fps_resolution_and_duration_from_ffprobe(library, make_clip):
    clip = library.import_clip("spiel-001", make_clip(duration=4), "clip1", 1, NO_PROFILE, {})

    assert clip.fps == pytest.approx(25.0)
    assert (clip.width, clip.height) == (320, 180)
    assert clip.duration_s == pytest.approx(4.0, abs=0.2)
    assert library.get_clip("spiel-001", "clip1").width == 320


# --- Regel 9: Original bleibt unverändert ---


@requires_ffmpeg
def test_import_copies_the_video_and_does_not_change_the_original(library, make_clip):
    original = make_clip("quelle.mp4")
    before = sha256(original)

    library.import_clip("spiel-001", original, "clip1", 1, NO_PROFILE, {})

    assert original.is_file()
    assert sha256(original) == before
    assert sha256(library.clip_dir("spiel-001", "clip1") / "clip.mp4") == before


# --- AK 1: ein Spiel, zwei Clips mit verschiedenen Profilen ---


@requires_ffmpeg
def test_one_match_with_two_clips_of_different_profiles_can_be_found_again(
    root, library, make_clip
):
    library.import_clip("spiel-001", make_clip("a.mp4"), "clip1", 1, STAND, {"detect_every": 10})
    library.import_clip("spiel-001", make_clip("b.mp4"), "clip2", 2, CORNER, {"detect_every": 2})

    clips = {c.id: c for c in FileLibrary(root).list_clips("spiel-001")}

    assert set(clips) == {"clip1", "clip2"}
    assert clips["clip1"].profile == STAND
    assert clips["clip2"].profile == CORNER
    assert clips["clip1"].settings == {"detect_every": 10}
    assert clips["clip2"].settings == {"detect_every": 2}


@requires_ffmpeg
def test_list_clips_filters_by_half(library, make_clip):
    library.import_clip("spiel-001", make_clip("a.mp4"), "clip1", 1, NO_PROFILE, {})
    library.import_clip("spiel-001", make_clip("b.mp4"), "clip2", 2, NO_PROFILE, {})
    library.import_clip("spiel-001", make_clip("c.mp4"), "clip3", None, NO_PROFILE, {})

    assert [c.id for c in library.list_clips("spiel-001", half=1)] == ["clip1"]
    assert [c.id for c in library.list_clips("spiel-001", half=2)] == ["clip2"]
    assert {c.id for c in library.list_clips("spiel-001")} == {"clip1", "clip2", "clip3"}


# --- Regel 6 und AK 1: zweiter Lauf überschreibt den ersten nicht ---


@requires_ffmpeg
def test_second_run_gets_its_own_folder_and_leaves_the_first_run_unchanged(library, make_clip):
    library.import_clip("spiel-001", make_clip(), "clip1", 1, NO_PROFILE, {})
    first = library.create_run("spiel-001", "clip1", {"detect_every": 5})
    first_file = library.run_dir("spiel-001", "clip1", first.id) / "run.json"
    first_bytes = first_file.read_bytes()

    second = library.create_run("spiel-001", "clip1", {"detect_every": 2})

    assert second.id != first.id
    assert library.run_dir("spiel-001", "clip1", second.id) != first_file.parent
    assert first_file.read_bytes() == first_bytes
    assert {r.id for r in library.list_runs("spiel-001", "clip1")} == {first.id, second.id}


# --- Regel 7: run.json enthält die aufgelösten Parameter ---


@requires_ffmpeg
def test_run_json_contains_the_resolved_settings_standard_profile_and_call(library, make_clip):
    clip = library.import_clip(
        "spiel-001", make_clip(), "clip1", 1, CORNER, {"detect_every": 2, "score_threshold": 0.5}
    )
    resolved = asdict(
        load_settings(profile_overrides=clip.settings, overrides={"score_threshold": 0.6})
    )

    run = library.create_run("spiel-001", "clip1", resolved)

    run_json = library.run_dir("spiel-001", "clip1", run.id) / "run.json"
    stored = json.loads(run_json.read_text(encoding="utf-8"))
    assert stored["settings"]["detect_every"] == 2  # aus dem Profil
    assert stored["settings"]["score_threshold"] == 0.6  # aus dem Aufruf
    assert stored["settings"]["tile_size"] == 640  # aus dem Standard
    assert stored["clip_id"] == "clip1"


# --- Regel 10: Schema-Version ---


@requires_ffmpeg
@pytest.mark.parametrize("bad_version", [0, SCHEMA_VERSION + 1, "x", None])
def test_foreign_or_old_schema_version_gives_clear_error_for_every_file_kind(
    root, library, make_clip, bad_version
):
    library.import_clip("spiel-001", make_clip(), "clip1", 1, NO_PROFILE, {})
    run = library.create_run("spiel-001", "clip1", {})
    files = {
        "match": root / "spiel-001" / "match.json",
        "clip": library.clip_dir("spiel-001", "clip1") / "clip.json",
        "run": library.run_dir("spiel-001", "clip1", run.id) / "run.json",
    }
    readers = {
        "match": lambda lib: lib.get_match("spiel-001"),
        "clip": lambda lib: lib.get_clip("spiel-001", "clip1"),
        "run": lambda lib: lib.list_runs("spiel-001", "clip1"),
    }
    for kind, path in files.items():
        data = json.loads(path.read_text(encoding="utf-8"))
        good = json.dumps(data)
        data["schema_version"] = bad_version
        path.write_text(json.dumps(data), encoding="utf-8")

        with pytest.raises(LibraryError, match="schema_version"):
            readers[kind](FileLibrary(root))

        path.write_text(good, encoding="utf-8")  # zurücksetzen für die nächste Dateiart


def test_match_file_carries_the_current_schema_version(root, library):
    data = json.loads((root / "spiel-001" / "match.json").read_text(encoding="utf-8"))

    assert data["schema_version"] == SCHEMA_VERSION


# --- Regel 11: Pfade relativ ---


@requires_ffmpeg
def test_paths_in_json_files_are_relative_to_the_library_root(root, library, make_clip):
    source = make_clip("quelle.mp4")
    library.import_clip("spiel-001", source, "clip1", 1, NO_PROFILE, {})
    run = library.create_run("spiel-001", "clip1", {})

    clip_json = library.clip_dir("spiel-001", "clip1") / "clip.json"
    run_json = library.run_dir("spiel-001", "clip1", run.id) / "run.json"
    for path in (root / "spiel-001" / "match.json", clip_json, run_json):
        text = path.read_text(encoding="utf-8")
        assert str(root) not in text, f"absoluter Pfad in {path.name}"
        assert str(source.parent) not in text, f"Quellpfad in {path.name}"
        assert "\\\\" not in text, f"Backslash-Pfad in {path.name}"

    stored = json.loads(clip_json.read_text(encoding="utf-8"))
    assert stored["source_file"] == "spiel-001/clip1/clip.mp4"
    assert (root / stored["source_file"]).is_file()
