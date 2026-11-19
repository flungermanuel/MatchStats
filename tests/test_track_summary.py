"""T4: Kennzahlen zu den Spuren (summarize_tracks), für Bericht und summary.json."""

import pytest
from matchstats.application.track_summary import summarize_tracks
from matchstats.domain.tracking import Track, TrackPoint

from matchstats.domain.result import RunResult


def _track(track_id: int, length: int, visible_every: int = 5) -> Track:
    points = tuple(
        TrackPoint(
            frame=i,
            x=0.0,
            y=0.0,
            w=20.0,
            h=50.0,
            visible=(i % visible_every == 0),
            score=0.9 if i % visible_every == 0 else None,
        )  # fmt: skip
        for i in range(length)
    )
    return Track(id=track_id, points=points)


def _result(tracks, frame_count=1500, fps=25.0) -> RunResult:
    return RunResult(
        source="clip.mp4", settings={}, tracks=tuple(tracks), fps=fps, frame_count=frame_count
    )


def test_summary_counts_tracks_per_minute_of_video():
    # 1500 Bilder bei 25 fps = 60 s = 1 Minute
    summary = summarize_tracks(_result([_track(1, 50), _track(2, 50), _track(3, 50)]))

    assert summary["track_count"] == 3
    assert summary["tracks_per_minute"] == pytest.approx(3.0)


def test_summary_tracks_per_minute_scales_with_clip_length():
    summary = summarize_tracks(_result([_track(1, 50), _track(2, 50)], frame_count=750))

    assert summary["tracks_per_minute"] == pytest.approx(4.0)  # 2 Spuren in 30 s


def test_summary_mean_track_length_is_given_in_seconds():
    # Spurlänge = Anzahl Punkte / fps: 50 Bilder = 2 s, 100 Bilder = 4 s -> Mittel 3 s
    summary = summarize_tracks(_result([_track(1, 50), _track(2, 100)]))

    assert summary["mean_track_seconds"] == pytest.approx(3.0)


def test_summary_visible_share_is_the_share_of_points_seen_by_the_detector():
    # Gleich lange Spuren, jeder 5. Punkt sichtbar -> 20 %
    summary = summarize_tracks(_result([_track(1, 100), _track(2, 100)]))

    assert summary["visible_share"] == pytest.approx(0.2)


def test_summary_without_tracks_has_zero_count_and_no_invented_values():
    summary = summarize_tracks(_result([]))

    assert summary["track_count"] == 0
    assert summary["visible_share"] is None
    assert summary["mean_track_seconds"] is None
