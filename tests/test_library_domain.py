"""T3b: Datentypen der Bibliothek (Spiel, Clip, Profil, Lauf) prüfen ihre Werte."""

import pytest
from matchstats.domain.library import (
    SCHEMA_VERSION,
    Clip,
    Match,
    RecordingProfile,
    RunInfo,
)

PROFILE = RecordingProfile(angle=None, camera_motion=None, notes="")


def make_clip(**changes) -> Clip:
    values = {
        "id": "clip1", "match_id": "spiel-001", "half": 1,
        "source_file": "spiel-001/clip1/clip.mp4",
        "fps": 25.0, "width": 1920, "height": 1080, "duration_s": 4.0,
        "profile": PROFILE, "settings": {},
    }  # fmt: skip
    values.update(changes)
    return Clip(**values)


def test_schema_version_is_a_positive_integer():
    assert isinstance(SCHEMA_VERSION, int)
    assert SCHEMA_VERSION >= 1


def test_match_and_run_info_can_be_created():
    assert Match(id="spiel-001", name="Testspiel", date=None, notes="").id == "spiel-001"
    run = RunInfo(id="run-1", created="2026-11-18T10:00:00", clip_id="clip1", settings={})
    assert run.clip_id == "clip1"


ANGLES = ["tribuene_hoch", "seitenlinie", "ecke", "hinter_tor", "sonstige"]


@pytest.mark.parametrize("angle", ANGLES)
def test_profile_accepts_every_known_angle(angle):
    assert RecordingProfile(angle=angle, camera_motion=None, notes="").angle == angle


@pytest.mark.parametrize("motion", ["fest", "schwenkt", "schwenkt_und_zoomt"])
def test_profile_accepts_every_known_camera_motion(motion):
    assert RecordingProfile(angle=None, camera_motion=motion, notes="").camera_motion == motion


def test_profile_accepts_unknown_values_as_none():
    profile = RecordingProfile(angle=None, camera_motion=None, notes="")

    assert profile.angle is None
    assert profile.camera_motion is None


def test_profile_rejects_unknown_angle():
    with pytest.raises(ValueError, match="angle"):
        RecordingProfile(angle="vogelperspektive", camera_motion=None, notes="")


def test_profile_rejects_unknown_camera_motion():
    with pytest.raises(ValueError, match="camera_motion"):
        RecordingProfile(angle=None, camera_motion="rast", notes="")


@pytest.mark.parametrize("half", [1, 2, None])
def test_clip_accepts_half_one_two_or_none(half):
    assert make_clip(half=half).half == half


@pytest.mark.parametrize("half", [0, 3, -1, "1"])
def test_clip_rejects_half_outside_one_two_none(half):
    with pytest.raises(ValueError, match="half"):
        make_clip(half=half)


@pytest.mark.parametrize("field", ["fps", "width", "height"])
@pytest.mark.parametrize("value", [0, -1])
def test_clip_rejects_zero_or_negative_fps_and_size(field, value):
    with pytest.raises(ValueError, match=field):
        make_clip(**{field: value})


def test_clip_rejects_negative_duration():
    with pytest.raises(ValueError, match="duration_s"):
        make_clip(duration_s=-1.0)
