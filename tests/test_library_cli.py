"""T3b: CLI-Befehle `match add`, `clip import`, `clip list` und `evaluate --game --half`."""

import json

import pytest
from matchstats.domain.library import Match, RecordingProfile
from matchstats.infrastructure.file_library import FileLibrary
from PIL import Image

from conftest import requires_ffmpeg
from matchstats.cli import main

NO_PROFILE = RecordingProfile(angle=None, camera_motion=None, notes="")


def _add_match(lib_root, match_id="spiel-001"):
    return main(["match", "add", match_id, "--name", "Testspiel", "--library", str(lib_root)])


# --- Smoke-Tests ---


def test_match_add_creates_the_match(tmp_path):
    lib = tmp_path / "lib"

    assert _add_match(lib) == 0
    assert FileLibrary(lib).get_match("spiel-001").name == "Testspiel"


def test_match_add_with_duplicate_id_fails_with_message(tmp_path, capsys):
    lib = tmp_path / "lib"
    _add_match(lib)

    assert _add_match(lib) != 0
    assert "spiel-001" in capsys.readouterr().err


@requires_ffmpeg
def test_clip_import_command_copies_the_video_into_the_library(tmp_path, make_clip):
    lib = tmp_path / "lib"
    _add_match(lib)

    code = main([
        "clip", "import", str(make_clip("quelle.mp4")), "--game", "spiel-001", "--clip", "clip1",
        "--half", "1", "--angle", "ecke", "--camera-motion", "fest", "--library", str(lib),
    ])  # fmt: skip

    assert code == 0
    clip = FileLibrary(lib).get_clip("spiel-001", "clip1")
    assert (clip.half, clip.profile.angle, clip.profile.camera_motion) == (1, "ecke", "fest")


def test_clip_import_into_unknown_game_fails_with_game_id(tmp_path, capsys):
    video = tmp_path / "x.mp4"
    video.write_bytes(b"dummy")

    code = main([
        "clip", "import", str(video), "--game", "spiel-999", "--clip", "clip1",
        "--library", str(tmp_path / "lib"),
    ])  # fmt: skip

    assert code != 0
    assert "spiel-999" in capsys.readouterr().err


@requires_ffmpeg
def test_clip_list_shows_clips_and_filters_by_half(tmp_path, make_clip, capsys):
    lib = tmp_path / "lib"
    _add_match(lib)
    for clip_id, half in (("clip1", "1"), ("clip2", "2")):
        main([
            "clip", "import", str(make_clip(f"{clip_id}.mp4")), "--game", "spiel-001",
            "--clip", clip_id, "--half", half, "--library", str(lib),
        ])  # fmt: skip
    capsys.readouterr()

    assert main(["clip", "list", "--game", "spiel-001", "--library", str(lib)]) == 0
    both = capsys.readouterr().out
    assert "clip1" in both and "clip2" in both

    assert main(["clip", "list", "--game", "spiel-001", "--half", "2", "--library", str(lib)]) == 0
    only_second = capsys.readouterr().out
    assert "clip2" in only_second and "clip1" not in only_second


def test_clip_list_for_unknown_game_fails(tmp_path):
    assert main(["clip", "list", "--game", "spiel-999", "--library", str(tmp_path / "lib")]) != 0


# --- Auswertung je Spiel und Halbzeit ---


class EmptyDetector:
    """Erkennt nie etwas: Recall 0, Precision fehlt. Reicht, um Zählung und Grenze zu prüfen."""

    def detect(self, image):
        return []


def _write_testset(lib: FileLibrary, match_id: str, clip_id: str, heights_per_image: list):
    """Legt in den Clip-Ordner ein kleines Testset (COCO) mit einfarbigen Bildern an."""
    testset = lib.clip_dir(match_id, clip_id) / "testset"
    (testset / "images").mkdir(parents=True)
    images, annotations = [], []
    for index, heights in enumerate(heights_per_image, start=1):
        name = f"{clip_id}_f{index:05d}.png"
        Image.new("RGB", (320, 180), (30, 30, 30)).save(testset / "images" / name)
        images.append({"id": index, "file_name": name, "width": 320, "height": 180})
        for n, h in enumerate(heights):
            annotations.append({
                "id": len(annotations) + 1, "image_id": index, "category_id": 1,
                "bbox": [10 + 40 * n, 10, 20, h],
            })  # fmt: skip
    coco = {
        "categories": [{"id": 1, "name": "team_a"}],
        "images": images,
        "annotations": annotations,
    }
    (testset / "coco.json").write_text(json.dumps(coco), encoding="utf-8")


@pytest.fixture
def two_halves(tmp_path, make_clip):
    """Spiel mit clip1 und clip2 (1. Halbzeit) und clip3 (2. Halbzeit), je kleines Testset."""
    lib = FileLibrary(tmp_path / "lib")
    lib.add_match(Match(id="spiel-001", name="Testspiel", date=None, notes=""))
    for clip_id, half in (("clip1", 1), ("clip2", 1), ("clip3", 2)):
        lib.import_clip("spiel-001", make_clip(f"{clip_id}.mp4"), clip_id, half, NO_PROFILE, {})
    # Boxhöhen aller Beschriftungen der 1. Halbzeit: 20, 20, 60, 100 -> Median 40.
    # Je Clip allein wäre der Median 20 (clip1) bzw. 80 (clip2): so fällt eine Grenze je Clip auf.
    _write_testset(lib, "spiel-001", "clip1", [[20], [20]])
    _write_testset(lib, "spiel-001", "clip2", [[60, 100]])
    _write_testset(lib, "spiel-001", "clip3", [[170]])  # gehört nicht zur 1. Halbzeit
    return lib


def _evaluate(tmp_path, monkeypatch, lib, half):
    monkeypatch.setattr(
        "matchstats.infrastructure.evaluation_job._build_detector",
        lambda name, settings: EmptyDetector(),
    )
    out = tmp_path / "bericht"
    code = main([
        "evaluate", "--game", "spiel-001", "--half", str(half), "--out", str(out),
        "--library", str(lib.root), "--detectors", "rfdetr", "--overlays", "1",
    ])  # fmt: skip
    return code, out


@requires_ffmpeg
def test_evaluate_combines_all_clips_of_one_half_into_one_report(tmp_path, monkeypatch, two_halves):
    code, out = _evaluate(tmp_path, monkeypatch, two_halves, 1)

    assert code == 0
    variants = json.loads((out / "report.json").read_text(encoding="utf-8"))["variants"]
    assert {v["name"] for v in variants} == {"rfdetr-whole", "rfdetr-tiles"}
    for variant in variants:
        assert variant["images"] == 3  # clip1 (2) + clip2 (1), clip3 gehört zur 2. Halbzeit
        assert variant["labels"] == 4


@requires_ffmpeg
def test_evaluate_uses_one_near_far_border_over_all_images_of_the_report(
    tmp_path, monkeypatch, two_halves
):
    _, out = _evaluate(tmp_path, monkeypatch, two_halves, 1)

    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["near_far_height_px"] == 40.0
    for variant in report["variants"]:
        assert (variant["labels_near"], variant["labels_far"]) == (2, 2)


@requires_ffmpeg
def test_evaluate_of_second_half_only_uses_clips_of_the_second_half(
    tmp_path, monkeypatch, two_halves
):
    _, out = _evaluate(tmp_path, monkeypatch, two_halves, 2)

    report = json.loads((out / "report.json").read_text(encoding="utf-8"))
    assert report["near_far_height_px"] == 170.0
    assert all(v["images"] == 1 for v in report["variants"])


@requires_ffmpeg
def test_evaluate_fails_with_message_when_game_has_no_clips_in_that_half(
    tmp_path, monkeypatch, two_halves, capsys
):
    code, out = _evaluate(tmp_path, monkeypatch, two_halves, 1)
    assert code == 0
    capsys.readouterr()

    lib = FileLibrary(tmp_path / "leer")
    lib.add_match(Match(id="spiel-001", name="Leer", date=None, notes=""))
    code = main([
        "evaluate", "--game", "spiel-001", "--half", "1", "--out", str(tmp_path / "x"),
        "--library", str(lib.root), "--detectors", "rfdetr",
    ])  # fmt: skip

    assert code != 0
    assert "spiel-001" in capsys.readouterr().err


def test_old_evaluate_arguments_are_still_accepted_by_the_parser():
    from matchstats.cli import build_parser

    argv = ["evaluate", "--testset", "a.json", "--images", "b", "--out", "o"]
    args = build_parser().parse_args(argv)

    assert str(args.testset) == "a.json"
