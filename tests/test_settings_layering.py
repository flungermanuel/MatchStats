"""T3b AK 2: Standard -> Profil-Überschreibungen -> Aufruf-Argumente (mit zwei Profilen)."""

import pytest

from matchstats.infrastructure.config_loader import load_settings

# Zwei Aufnahme-Profile, die je andere Parameter überschreiben (reine Daten).
PROFILE_FIXED = {"detect_every": 10, "tile_size": 960}
PROFILE_PANNING = {"detect_every": 2, "score_threshold": 0.5}


def test_defaults_apply_when_no_profile_and_no_call_overrides():
    assert load_settings().detect_every == 5


def test_existing_call_with_config_path_still_works(tmp_path):
    config = tmp_path / "eigene.toml"
    config.write_text("detect_every = 7\n", encoding="utf-8")

    assert load_settings(config).detect_every == 7


def test_profile_overrides_beat_defaults():
    settings = load_settings(profile_overrides=PROFILE_FIXED)

    assert settings.detect_every == 10
    assert settings.tile_size == 960


def test_values_the_profile_does_not_set_stay_at_default():
    settings = load_settings(profile_overrides=PROFILE_FIXED)

    assert settings.score_threshold == 0.3


def test_two_profiles_give_different_settings_from_the_same_defaults():
    fixed = load_settings(profile_overrides=PROFILE_FIXED)
    panning = load_settings(profile_overrides=PROFILE_PANNING)

    assert (fixed.detect_every, fixed.score_threshold) == (10, 0.3)
    assert (panning.detect_every, panning.score_threshold) == (2, 0.5)
    assert panning.tile_size == 640  # Standard, vom zweiten Profil nicht überschrieben


def test_call_overrides_beat_profile_overrides():
    settings = load_settings(profile_overrides=PROFILE_PANNING, overrides={"detect_every": 3})

    assert settings.detect_every == 3
    assert settings.score_threshold == 0.5  # Profilwert bleibt, wo der Aufruf nichts sagt


def test_call_overrides_beat_defaults_without_profile():
    assert load_settings(overrides={"nms_iou": 0.4}).nms_iou == 0.4


def test_unknown_key_in_profile_overrides_is_rejected_with_key_name():
    with pytest.raises(ValueError, match="detect_evry"):
        load_settings(profile_overrides={"detect_evry": 3})


def test_unknown_key_in_call_overrides_is_rejected_with_key_name():
    with pytest.raises(ValueError, match="tile_sise"):
        load_settings(overrides={"tile_sise": 3})


def test_invalid_value_after_merging_is_rejected_by_settings():
    with pytest.raises(ValueError, match="detect_every"):
        load_settings(profile_overrides={"detect_every": 0})


def test_invalid_call_value_is_rejected_even_if_profile_value_is_valid():
    with pytest.raises(ValueError, match="score_threshold"):
        load_settings(profile_overrides={"score_threshold": 0.5}, overrides={"score_threshold": 2})
