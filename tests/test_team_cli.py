"""T5a (b): `run_team_evaluation` und CLI `evaluate-teams` (Fake-Klassifikator, kleines Testset)."""

import json

import pytest
from PIL import Image

from conftest import requires_ffmpeg
from matchstats.application.library import LibraryError
from matchstats.application.team_evaluation import TeamEvaluationRun
from matchstats.cli import main
from matchstats.domain.library import Match, RecordingProfile
from matchstats.domain.settings import Settings
from matchstats.domain.teams import TeamPrediction, accuracy
from matchstats.infrastructure.evaluation_job import run_team_evaluation
from matchstats.infrastructure.file_library import FileLibrary

NO_PROFILE = RecordingProfile(angle=None, camera_motion=None, notes="")
CLASS_BY_X = {10: "team_a", 50: "team_b", 90: "goalkeeper", 130: "team_a"}  # 130 = Fehler


class FakeClassifier:
    """Sagt je nach Box-x voraus; beim Schiedsrichter (x = 130) absichtlich falsch."""

    def classify(self, images, boxes):
        return [TeamPrediction(CLASS_BY_X[int(b.x)], 0.9) for b in boxes]


def _write_testset(lib: FileLibrary, clip_id: str, labels_per_image: list[list[str]]) -> None:
    testset = lib.clip_dir("spiel-001", clip_id) / "testset"
    (testset / "images").mkdir(parents=True)
    categories = [{"id": i + 1, "name": n} for i, n in
                  enumerate(("team_a", "team_b", "goalkeeper", "referee"))]  # fmt: skip
    ids = {c["name"]: c["id"] for c in categories}
    images, annotations = [], []
    for index, labels in enumerate(labels_per_image, start=1):
        name = f"{clip_id}_f{index:05d}.png"
        Image.new("RGB", (320, 180), (30, 30, 30)).save(testset / "images" / name)
        images.append({"id": index, "file_name": name, "width": 320, "height": 180})
        for n, label in enumerate(labels):
            annotations.append({
                "id": len(annotations) + 1, "image_id": index, "category_id": ids[label],
                "bbox": [10 + 40 * n, 10, 20, 60],
            })  # fmt: skip
    coco = {"categories": categories, "images": images, "annotations": annotations}
    (testset / "coco.json").write_text(json.dumps(coco), encoding="utf-8")


@pytest.fixture
def library(tmp_path, make_clip, monkeypatch):
    lib = FileLibrary(tmp_path / "lib")
    lib.add_match(Match(id="spiel-001", name="Testspiel", date=None, notes=""))
    for clip_id, half in (("clip1", 1), ("clip2", 1), ("clip3", 2)):
        lib.import_clip("spiel-001", make_clip(f"{clip_id}.mp4"), clip_id, half, NO_PROFILE, {})
    ok = ["team_a", "team_b", "goalkeeper"]
    _write_testset(lib, "clip1", [ok, ok])
    _write_testset(lib, "clip2", [ok, [*ok, "referee"], ok])  # nur Bild 2 hat einen Fehler
    _write_testset(lib, "clip3", [ok])
    monkeypatch.setattr(
        "matchstats.infrastructure.evaluation_job._build_team_classifier",
        lambda settings: FakeClassifier(),
    )
    return lib


def _empty_library(tmp_path) -> FileLibrary:
    lib = FileLibrary(tmp_path / "leer")
    lib.add_match(Match(id="spiel-001", name="Leer", date=None, notes=""))
    return lib


def test_team_evaluation_without_any_labeled_images_raises_library_error(tmp_path):
    with pytest.raises(LibraryError, match="spiel-001"):
        run_team_evaluation(_empty_library(tmp_path), "spiel-001", 1, tmp_path / "out", Settings())


@requires_ffmpeg
def test_team_evaluation_measures_all_clips_of_the_half_and_writes_report(library, tmp_path):
    out = tmp_path / "bericht"

    run = run_team_evaluation(library, "spiel-001", 1, out, Settings(), overlay_count=1)

    assert isinstance(run, TeamEvaluationRun)
    assert set(run.clip_mappings) == {"clip1", "clip2"}  # clip3 gehört zur 2. Halbzeit
    assert set(run.predictions) == {
        "clip1/clip1_f00001.png", "clip1/clip1_f00002.png",
        "clip2/clip2_f00001.png", "clip2/clip2_f00002.png", "clip2/clip2_f00003.png",
    }  # fmt: skip
    assert accuracy(run.confusion) == 15 / 16  # 16 Boxen, 1 Schiedsrichter falsch
    assert (out / "team_report.json").is_file()
    assert (out / "team_report.md").is_file()


@requires_ffmpeg
def test_team_evaluation_writes_overlay_of_the_image_with_the_error_first(library, tmp_path):
    out = tmp_path / "bericht"

    run_team_evaluation(library, "spiel-001", 1, out, Settings(), overlay_count=1)

    files = list((out / "overlays").rglob("*.png"))
    assert [f.name for f in files] == ["clip2_f00002.png"]


@requires_ffmpeg
def test_evaluate_teams_command_succeeds_and_prints_report_path(library, tmp_path, capsys):
    out = tmp_path / "bericht"

    code = main([
        "evaluate-teams", "--game", "spiel-001", "--half", "1", "--out", str(out),
        "--library", str(library.root), "--overlays", "2",
    ])  # fmt: skip

    assert code == 0
    assert "team_report.md" in capsys.readouterr().out
    data = json.loads((out / "team_report.json").read_text(encoding="utf-8"))
    assert data["schema_version"] == 1
    assert len(list((out / "overlays").rglob("*.png"))) == 2


def test_evaluate_teams_command_without_half_fails_with_exit_code_2(tmp_path):
    argv = ["evaluate-teams", "--game", "spiel-001", "--out", str(tmp_path / "o")]
    try:
        code = main(argv)
    except SystemExit as exit_:  # argparse darf selbst mit 2 abbrechen
        code = exit_.code

    assert code == 2


def test_evaluate_teams_command_for_game_without_testsets_fails_with_message(tmp_path, capsys):
    lib = _empty_library(tmp_path)

    code = main([
        "evaluate-teams", "--game", "spiel-001", "--half", "1", "--out", str(tmp_path / "o"),
        "--library", str(lib.root),
    ])  # fmt: skip

    assert code == 2
    assert "spiel-001" in capsys.readouterr().err


def test_evaluate_teams_command_accepts_overlays_and_config_options():
    from matchstats.cli import build_parser

    argv = ["evaluate-teams", "--game", "g", "--half", "2", "--out", "o", "--overlays", "3",
            "--config", "c.toml"]  # fmt: skip
    args = build_parser().parse_args(argv)

    assert (args.game, args.half, args.overlays) == ("g", 2, 3)
    assert str(args.config) == "c.toml"
