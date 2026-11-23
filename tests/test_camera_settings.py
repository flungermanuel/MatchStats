"""T4b: Aufnahme-Profil (camera_motion) als Parameterschicht zwischen Datei und Clip-Profil."""

from matchstats.domain.settings import Settings
from matchstats.infrastructure.config_loader import load_settings


def test_camera_settings_have_defaults():
    settings = Settings()

    assert isinstance(settings.camera_compensation, bool)
    assert 0.0 < settings.camera_downscale <= 1.0
    assert settings.camera_max_features > 0
    assert settings.camera_min_quality >= 0.0


def test_fixed_camera_profile_turns_compensation_off():
    assert load_settings(camera_motion="fest").camera_compensation is False


def test_panning_profile_turns_compensation_on():
    assert load_settings(camera_motion="schwenkt").camera_compensation is True


def test_panning_and_zooming_profile_turns_compensation_on():
    assert load_settings(camera_motion="schwenkt_und_zoomt").camera_compensation is True


def test_unknown_camera_profile_turns_compensation_on():
    assert load_settings(camera_motion=None).camera_compensation is True
    assert load_settings().camera_compensation is True


def test_call_argument_overrides_camera_profile():
    off = load_settings(camera_motion="schwenkt", overrides={"camera_compensation": False})
    on = load_settings(camera_motion="fest", overrides={"camera_compensation": True})

    assert off.camera_compensation is False
    assert on.camera_compensation is True


def test_clip_settings_override_camera_profile():
    settings = load_settings(camera_motion="fest", profile_overrides={"camera_compensation": True})

    assert settings.camera_compensation is True


def test_camera_profile_beats_values_from_a_config_file(tmp_path):
    config = tmp_path / "eigene.toml"
    config.write_text("camera_compensation = false\n", encoding="utf-8")

    assert load_settings(config, camera_motion="schwenkt").camera_compensation is True


def test_camera_profile_leaves_other_parameters_at_default():
    assert load_settings(camera_motion="fest").detect_every == load_settings().detect_every
