"""Darstellung der Spuren: Video mit Box und ID (halbe Geschwindigkeit) und Kontaktbögen.

Deterministisch aus den gespeicherten Spuren; das Video wird Bild für Bild gelesen und
geschrieben. Gesehene Boxen sind dick gezeichnet, überbrückte dünn.
"""

import colorsys
from collections import defaultdict
from pathlib import Path

import cv2
import numpy as np

from matchstats.application.tracking_stages import FrameSource
from matchstats.domain.result import RunResult
from matchstats.domain.tracking import TrackPoint

SHEET_INTERVAL_S = 2.0  # ein Kontaktbogen-Bild alle 2 Sekunden
SHEET_SCALE = 1.0  # volle Auflösung, damit IDs ferner Spieler lesbar bleiben
LABEL_SCALE = 0.75  # Schriftgröße der ID


def color_for_id(track_id: int) -> tuple[int, int, int]:
    """Feste Farbe (BGR) je ID: Farbton über den goldenen Schnitt verteilt."""
    hue = (track_id * 0.618033988749895) % 1.0
    r, g, b = colorsys.hsv_to_rgb(hue, 0.9, 1.0)
    return int(b * 255), int(g * 255), int(r * 255)


def _draw(bgr: np.ndarray, boxes: list[tuple[int, TrackPoint]]) -> None:
    for track_id, p in boxes:
        color = color_for_id(track_id)
        top_left = (round(p.x), round(p.y))
        bottom_right = (round(p.x + p.w), round(p.y + p.h))
        cv2.rectangle(bgr, top_left, bottom_right, color, 2 if p.visible else 1)
        origin = (top_left[0], max(16, top_left[1] - 4))
        text = str(track_id)
        font = cv2.FONT_HERSHEY_SIMPLEX
        # Dunkler Rand unter der farbigen Schrift: lesbar auf Rasen und Tribüne.
        cv2.putText(bgr, text, origin, font, LABEL_SCALE, (0, 0, 0), 4, cv2.LINE_AA)
        cv2.putText(bgr, text, origin, font, LABEL_SCALE, color, 2, cv2.LINE_AA)


def render_tracks(source: FrameSource, result: RunResult, out_dir: Path) -> None:
    """Schreibt out_dir/tracks.mp4 (halbe Geschwindigkeit) und out_dir/sheet_*.png."""
    out_dir.mkdir(parents=True, exist_ok=True)
    by_frame: dict[int, list[tuple[int, TrackPoint]]] = defaultdict(list)
    for track in result.tracks:
        for point in track.points:
            by_frame[point.frame].append((track.id, point))

    width, height = source.frame_size
    sheet_every = max(1, round(SHEET_INTERVAL_S * source.fps))
    writer = cv2.VideoWriter(
        str(out_dir / "tracks.mp4"),
        cv2.VideoWriter_fourcc(*"mp4v"),
        source.fps / 2,
        (width, height),
    )
    if not writer.isOpened():
        writer.release()
        raise OSError(f"Videodatei konnte nicht geschrieben werden: {out_dir / 'tracks.mp4'}")
    try:
        for index, rgb in source.frames(1):
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            _draw(bgr, by_frame.get(index, []))
            writer.write(bgr)
            if index % sheet_every == 0:
                _save_sheet(bgr, index / source.fps, out_dir / f"sheet_{index:06d}.png")
    finally:
        writer.release()


def _save_sheet(bgr: np.ndarray, seconds: float, path: Path) -> None:
    if SHEET_SCALE != 1.0:
        small = cv2.resize(bgr, None, fx=SHEET_SCALE, fy=SHEET_SCALE, interpolation=cv2.INTER_AREA)
    else:
        small = bgr.copy()
    label = f"t = {seconds:.1f} s"
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(small, label, (10, 30), font, 0.9, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(small, label, (10, 30), font, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    cv2.imwrite(str(path), small)
