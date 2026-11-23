"""T4: `matchstats track` Ende-zu-Ende mit winzigem synthetischem Video und Fake-Detektor."""

import json

import numpy as np
import pytest

from conftest import requires_ffmpeg
from matchstats.cli import main
from matchstats.domain.detection import Detection
from matchstats.infrastructure.file_library import FileLibrary
from matchstats.infrastructure.result_store import load_result

cv2 = pytest.importorskip("cv2")

pytestmark = requires_ffmpeg

GAME, CLIP = "spiel-001", "clip1"


class CountingDetector:
    """Sieht in jedem Bild dieselbe Person (stillstehend) und zählt die Aufrufe."""

    def __init__(self) -> None:
        self.calls = 0

    def detect(self, image):
        self.calls += 1
        return [Detection(60.0, 20.0, 12.0, 30.0, 0.9)]


def _write_video(path, frames=30, size=(160, 90), fps=25):
    writer = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, size)
    for index in range(frames):
        image = np.full((size[1], size[0], 3), 40 + index, dtype=np.uint8)
        writer.write(image)
    writer.release()


@pytest.fixture
def library(tmp_path):
    root = tmp_path / "lib"
    video = tmp_path / "quelle.mp4"
    _write_video(video)
    assert main(["match", "add", GAME, "--name", "Testspiel", "--library", str(root)]) == 0
    code = main(["clip", "import", str(video), "--game", GAME, "--clip", CLIP,
                 "--library", str(root)])  # fmt: skip
    assert code == 0
    return FileLibrary(root)


@pytest.fixture
def detector(monkeypatch):
    fake = CountingDetector()
    monkeypatch.setattr(
        "matchstats.infrastructure.tracking_job.build_detector", lambda variant, settings: fake
    )
    return fake


def _track(library, *extra):
    return main(["track", "--game", GAME, "--clip", CLIP, "--library", str(library.root), *extra])


def test_track_creates_a_new_run_with_detections_tracks_and_summary(library, detector):
    assert _track(library, "--no-render") == 0

    runs = library.list_runs(GAME, CLIP)
    assert len(runs) == 1
    run_dir = library.run_dir(GAME, CLIP, runs[0].id)
    for name in ("detections.json", "tracks.json", "summary.json"):
        assert (run_dir / name).is_file(), name
    result = load_result(run_dir / "tracks.json")
    assert result.schema_version == 2
    assert len(result.tracks) == 1  # die stillstehende Fake-Person
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["track_count"] == 1


def test_track_without_run_option_creates_a_new_run_each_time(library, detector):
    _track(library, "--no-render")
    _track(library, "--no-render")

    assert [r.id for r in library.list_runs(GAME, CLIP)] == ["run-001", "run-002"]


def test_track_with_existing_run_reuses_the_detections_without_calling_the_detector(
    library, detector
):
    assert _track(library, "--no-render") == 0
    calls_after_first = detector.calls
    assert calls_after_first > 0

    assert _track(library, "--run", "run-001", "--no-render") == 0

    assert detector.calls == calls_after_first
    assert [r.id for r in library.list_runs(GAME, CLIP)] == ["run-001"]


def test_track_with_no_render_creates_no_render_folder(library, detector):
    _track(library, "--no-render")

    run_dir = library.run_dir(GAME, CLIP, "run-001")
    assert not (run_dir / "render").exists()


def test_track_with_render_creates_video_and_contact_sheets(library, detector):
    assert _track(library) == 0

    render = library.run_dir(GAME, CLIP, "run-001") / "render"
    assert (render / "tracks.mp4").is_file()
    assert len(list(render.glob("sheet_*.png"))) >= 1


def test_track_for_unknown_clip_fails_with_clip_id_in_message(library, detector, capsys):
    code = main(["track", "--game", GAME, "--clip", "clip-gibts-nicht",
                 "--library", str(library.root)])  # fmt: skip

    assert code != 0
    assert "clip-gibts-nicht" in capsys.readouterr().err


def test_summary_has_no_detection_seconds_when_the_detections_were_reused(library, detector):
    _track(library, "--no-render")
    _track(library, "--run", "run-001", "--no-render")

    run_dir = library.run_dir(GAME, CLIP, "run-001")
    summary = json.loads((run_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["detections_reused"] is True
    assert summary["stage_seconds"]["detection"] is None


def _summary(library, run_id="run-001"):
    path = library.run_dir(GAME, CLIP, run_id) / "summary.json"
    return json.loads(path.read_text(encoding="utf-8"))


def test_summary_has_schema_version_3_with_camera_fields(library, detector):
    _track(library, "--no-render")

    summary = _summary(library)
    assert summary["schema_version"] == 3
    assert "camera_compensation" in summary
    assert "camera_null_share" in summary


def test_track_with_no_camera_runs_without_compensation_and_reports_no_null_share(
    library, detector
):
    assert _track(library, "--no-camera", "--no-render") == 0

    summary = _summary(library)
    assert summary["camera_compensation"] is False
    assert summary["camera_null_share"] is None  # ohne Ausgleich gelaufen, nicht 0


def test_track_with_camera_reports_the_share_of_failed_estimates(library, detector):
    assert _track(library, "--camera", "--no-render") == 0

    summary = _summary(library)
    assert summary["camera_compensation"] is True
    # Das Testvideo ist einfarbig (keine Merkmale): Schätzung scheitert in allen Bildern
    assert summary["camera_null_share"] == 1.0


def test_track_with_run_and_config_warns_that_config_is_ignored(
    library, detector, tmp_path, capsys
):
    _track(library, "--no-render")
    config = tmp_path / "eigene.toml"
    config.write_text("detect_every = 7\n", encoding="utf-8")
    capsys.readouterr()

    code = _track(library, "--run", "run-001", "--config", str(config), "--no-render")

    assert code == 0
    assert "--config" in capsys.readouterr().err


def test_track_with_run_holding_unknown_settings_fails_with_readable_error(
    library, detector, capsys
):
    run = library.create_run(GAME, CLIP, {"gibt_es_nicht": 1})

    code = _track(library, "--run", run.id, "--no-render")

    assert code != 0
    assert "gibt_es_nicht" in capsys.readouterr().err
