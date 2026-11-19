"""Kennzahlen zu den Spuren eines Laufs (für Bericht und summary.json)."""

from typing import Any

from matchstats.domain.result import RunResult


def summarize_tracks(result: RunResult) -> dict[str, Any]:
    """Anzahl, Spuren pro Minute, mittlere Spurlänge (s), Anteil gesehener Punkte.

    Ohne Spuren (oder ohne fps) bleiben abgeleitete Werte None statt erfundener Zahlen.
    """
    tracks = result.tracks
    count = len(tracks)
    fps = result.fps
    minutes = (
        result.frame_count / fps / 60 if fps and result.frame_count else None
    )  # None: Clip-Länge unbekannt
    total_points = sum(len(t.points) for t in tracks)
    seen_points = sum(p.visible for t in tracks for p in t.points)
    return {
        "track_count": count,
        "tracks_per_minute": count / minutes if minutes else None,
        "mean_track_seconds": (
            sum(len(t.points) / fps for t in tracks) / count if count and fps else None
        ),
        "visible_share": seen_points / total_points if total_points else None,
    }
