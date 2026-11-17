"""Parameter kommen aus der Konfiguration, nicht fest aus dem Code."""

import pytest

from matchstats.domain.settings import Settings
from matchstats.infrastructure.config_loader import load_settings


def test_default_settings_have_detect_every_5():
    assert load_settings().detect_every == 5


def test_default_settings_sample_20_frames_per_clip():
    assert load_settings().frames_per_clip == 20


def test_frames_per_clip_must_be_at_least_1():
    with pytest.raises(ValueError):
        Settings(frames_per_clip=0)


def test_frames_per_clip_can_be_overridden_by_file(tmp_path):
    cfg = tmp_path / "mein.toml"
    cfg.write_text("frames_per_clip = 7\n", encoding="utf-8")

    assert load_settings(cfg).frames_per_clip == 7


def test_settings_can_be_overridden_by_file(tmp_path):
    cfg = tmp_path / "mein.toml"
    cfg.write_text("detect_every = 10\n", encoding="utf-8")

    assert load_settings(cfg).detect_every == 10
