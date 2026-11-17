"""T2: Testbilder werden gleichmäßig gezogen, nicht von Hand ausgesucht."""

import dataclasses

import pytest
from matchstats.domain.sampling import SampledFrame, frame_number, uniform_timestamps


def test_uniform_timestamps_returns_requested_count():
    assert len(uniform_timestamps(60.0, 20)) == 20


def test_uniform_timestamps_are_midpoints_of_equal_sections():
    stamps = uniform_timestamps(60.0, 20)

    for i, t in enumerate(stamps):
        assert t == pytest.approx((i + 0.5) * 3.0)


def test_uniform_timestamps_are_evenly_spaced():
    stamps = uniform_timestamps(60.0, 20)
    gaps = [b - a for a, b in zip(stamps, stamps[1:], strict=False)]

    assert gaps == pytest.approx([3.0] * 19)


def test_uniform_timestamps_lie_strictly_inside_the_clip():
    stamps = uniform_timestamps(60.0, 20)

    assert all(0 < t < 60.0 for t in stamps)
    assert stamps == sorted(stamps)


def test_uniform_timestamps_single_frame_is_clip_middle():
    assert uniform_timestamps(10.0, 1) == pytest.approx([5.0])


@pytest.mark.parametrize("count", [0, -1])
def test_uniform_timestamps_reject_count_below_one(count):
    with pytest.raises(ValueError):
        uniform_timestamps(60.0, count)


@pytest.mark.parametrize("duration", [0.0, -5.0])
def test_uniform_timestamps_reject_non_positive_duration(duration):
    with pytest.raises(ValueError):
        uniform_timestamps(duration, 20)


def test_frame_number_rounds_time_times_fps_to_nearest_frame():
    assert frame_number(1.48, 25.0) == 37  # 37.0
    assert frame_number(1.5, 25.0) == 38  # 37.5 -> 38 (aufgerundet, kein Abschneiden)
    assert frame_number(1.49, 25.0) == 37  # 37.25 -> 37


def test_frame_number_is_an_int():
    assert isinstance(frame_number(2.0, 25.0), int)


def test_sampled_frame_is_immutable_and_has_expected_fields():
    frame = SampledFrame(
        clip="clip1.mp4", time_s=1.5, frame_number=38, file_name="clip1_f00038.png"
    )

    assert [f.name for f in dataclasses.fields(frame)] == [
        "clip",
        "time_s",
        "frame_number",
        "file_name",
    ]
    with pytest.raises(dataclasses.FrozenInstanceError):
        frame.time_s = 2.0  # type: ignore[misc]
