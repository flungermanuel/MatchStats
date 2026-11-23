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
from matchstats.domain.id_switch import IdSwitchCandidate
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


SWITCH_CROP = (480, 270)  # Ausschnitt um die Stelle des möglichen Wechsels (Pixel)
SWITCH_ZOOM = 2  # Vergrößerung des Ausschnitts


def _switch_crop(
    bgr: np.ndarray, point: TrackPoint, center: tuple[float, float], label: str
) -> np.ndarray:
    """Ausschnitt um `center` mit rot markierter Box und Beschriftung (Bild bleibt unverändert)."""
    marked = bgr.copy()
    cv2.rectangle(
        marked,
        (round(point.x), round(point.y)),
        (round(point.x + point.w), round(point.y + point.h)),
        (0, 0, 255),
        3,
    )
    height, width = marked.shape[:2]
    crop_w, crop_h = SWITCH_CROP
    left = int(min(max(center[0] - crop_w / 2, 0), max(width - crop_w, 0)))
    top = int(min(max(center[1] - crop_h / 2, 0), max(height - crop_h, 0)))
    crop = marked[top : top + crop_h, left : left + crop_w]
    crop = cv2.resize(crop, None, fx=SWITCH_ZOOM, fy=SWITCH_ZOOM, interpolation=cv2.INTER_CUBIC)
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(crop, label, (10, 30), font, 0.9, (0, 0, 0), 4, cv2.LINE_AA)
    cv2.putText(crop, label, (10, 30), font, 0.9, (255, 255, 255), 2, cv2.LINE_AA)
    return crop


def render_tracks(
    source: FrameSource,
    result: RunResult,
    out_dir: Path,
    candidates: tuple[IdSwitchCandidate, ...] = (),
) -> None:
    """Schreibt out_dir/tracks.mp4 (halbe Geschwindigkeit), out_dir/sheet_*.png und je
    Kandidat für einen ID-Wechsel out_dir/switches/switch_NNN.png (links: letztes Bild der
    alten Spur, rechts: erstes Bild der neuen Spur, gleicher Ausschnitt). Die Kandidaten müssen aus
    `result` berechnet sein. Liefert die Videoquelle weniger Bilder als frame_count, fehlt das Bild
    des betroffenen Kandidaten ohne Fehlermeldung."""
    out_dir.mkdir(parents=True, exist_ok=True)
    point_at = {
        (t.id, p.frame): p for t in result.tracks for p in t.points
    }  # (Spur-ID, Bild) -> Punkt
    wanted: dict[int, list[tuple[int, int]]] = defaultdict(list)  # Bild -> [(Kandidat, 0|1)]
    for number, c in enumerate(candidates, start=1):
        wanted[c.end_frame].append((number, 0))
        wanted[c.start_frame].append((number, 1))
    halves: dict[tuple[int, int], np.ndarray] = {}
    if candidates:
        (out_dir / "switches").mkdir(exist_ok=True)
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
            for number, side in wanted.get(index, []):
                c = candidates[number - 1]
                old_end = point_at[(c.old_id, c.end_frame)]
                center = (old_end.x + old_end.w / 2, old_end.y + old_end.h / 2)
                if side == 0:
                    halves[(number, 0)] = _switch_crop(
                        bgr, old_end, center, f"alt: ID {c.old_id}, t = {index / source.fps:.1f} s"
                    )
                else:
                    new_start = point_at[(c.new_id, c.start_frame)]
                    label = f"neu: ID {c.new_id}, t = {index / source.fps:.1f} s"
                    halves[(number, 1)] = _switch_crop(bgr, new_start, center, label)
                if (number, 0) in halves and (number, 1) in halves:
                    pair = np.hstack([halves.pop((number, 0)), halves.pop((number, 1))])
                    cv2.imwrite(str(out_dir / "switches" / f"switch_{number:03d}.png"), pair)
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
