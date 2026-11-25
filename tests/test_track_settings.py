"""T4: neue Parameter des Trackings (Standardwerte aus default.toml, Prüfungen)."""

import pytest

from matchstats.domain.settings import Settings
from matchstats.infrastructure.config_loader import load_settings


def test_default_toml_provides_the_tracking_parameters():
    settings = load_settings()

    assert settings.detect_min_score == 0.1
    assert settings.track_high_score == 0.4
    assert settings.track_match_iou == 0.3
    assert settings.track_max_lost_seconds == 1.5
    assert settings.track_min_hits == 3
    assert settings.track_edge_margin_px == 40


def test_tracking_parameters_can_be_overridden_by_file(tmp_path):
    cfg = tmp_path / "mein.toml"
    cfg.write_text("track_min_hits = 4\ntrack_max_lost_seconds = 2.0\n", encoding="utf-8")

    settings = load_settings(cfg)

    assert (settings.track_min_hits, settings.track_max_lost_seconds) == (4, 2.0)


@pytest.mark.parametrize(
    "kwargs",
    [
        {"detect_min_score": -0.1},
        {"detect_min_score": 1.1},
        {"track_high_score": -0.1},
        {"track_high_score": 1.1},
        {"track_match_iou": -0.1},
        {"track_match_iou": 1.1},
        {"track_max_lost_seconds": -1.0},
        {"track_min_hits": 0},
        {"track_edge_margin_px": -1},
    ],
)
def test_invalid_tracking_parameters_are_rejected(kwargs):
    with pytest.raises(ValueError):
        Settings(**kwargs)


def test_invalid_tracking_parameter_in_file_names_the_parameter(tmp_path):
    cfg = tmp_path / "mein.toml"
    cfg.write_text("track_min_hits = 0\n", encoding="utf-8")

    with pytest.raises(ValueError, match="track_min_hits"):
        load_settings(cfg)


def test_team_vote_min_box_height_defaults_to_zero_filter_off():
    assert Settings().team_vote_min_box_height == 0.0


def test_negative_team_vote_min_box_height_is_rejected():
    with pytest.raises(ValueError):
        Settings(team_vote_min_box_height=-1.0)


def test_team_vote_min_box_height_zero_is_valid():
    assert Settings(team_vote_min_box_height=0.0).team_vote_min_box_height == 0.0
