"""Parameter kommen aus der Konfiguration, nicht fest aus dem Code."""

from matchstats.infrastructure.config_loader import load_settings


def test_default_settings_have_detect_every_5():
    assert load_settings().detect_every == 5


def test_settings_can_be_overridden_by_file(tmp_path):
    cfg = tmp_path / "mein.toml"
    cfg.write_text("detect_every = 10\n", encoding="utf-8")

    assert load_settings(cfg).detect_every == 10
