"""Kandidaten für ID-Wechsel: eine Spur endet mitten im Bild, nahebei beginnt kurz danach eine neue.

Das ist ein Indikator, keine Zählung: Ein anderer Mensch in der Nähe zählt mit (zu viel), eine
größere Lücke fällt durch (zu wenig). Wer am Bildrand oder mit dem Clip endet, verlässt das Bild
und gilt nicht als Kandidat. Geprüft wird nur das Ende der alten Spur: Beginnt die neue Spur am
Bildrand (Spieler tritt ein), zählt sie trotzdem, wenn nahebei eine alte endet. Der Abstand wird in
Boxhöhen der alten Spur gemessen, bei fernen (kleinen) Spielern ist die Schwelle in Pixeln also eng.
"""

import math
from dataclasses import dataclass

from matchstats.domain.settings import Settings
from matchstats.domain.tracking import Track, TrackPoint


@dataclass(frozen=True)
class IdSwitchCandidate:
    old_id: int
    new_id: int
    end_frame: int  # letztes Bild der alten Spur
    start_frame: int  # erstes Bild der neuen Spur
    distance_in_heights: float  # Abstand der Boxmitten, in Boxhöhen der alten Spur


def _center(p: TrackPoint) -> tuple[float, float]:
    return p.x + p.w / 2, p.y + p.h / 2


def _touches_edge(p: TrackPoint, frame_size: tuple[int, int], margin: int) -> bool:
    width, height = frame_size
    return p.x < margin or p.y < margin or p.x + p.w > width - margin or p.y + p.h > height - margin


def find_id_switch_candidates(
    tracks: tuple[Track, ...] | list[Track],
    fps: float,
    frame_size: tuple[int, int],
    frame_count: int,
    settings: Settings,
) -> tuple[IdSwitchCandidate, ...]:
    """Ordnet jeder neuen Spur höchstens eine alte zu (nächste zuerst) und umgekehrt."""
    max_gap = round(settings.switch_max_gap_seconds * fps)
    pairs: list[IdSwitchCandidate] = []
    for old in tracks:
        if not old.points:
            continue
        last = old.points[-1]
        if last.frame >= frame_count - 1:
            continue  # Clip-Ende
        if _touches_edge(last, frame_size, settings.track_edge_margin_px):
            continue  # Austritt aus dem Bild
        ox, oy = _center(last)
        for new in tracks:
            if new is old or not new.points:
                continue
            first = new.points[0]
            gap = first.frame - last.frame
            if not 1 <= gap <= max_gap:
                continue
            nx, ny = _center(first)
            distance = math.hypot(nx - ox, ny - oy) / last.h if last.h > 0 else math.inf
            if distance <= settings.switch_max_distance_heights:
                pairs.append(IdSwitchCandidate(old.id, new.id, last.frame, first.frame, distance))

    chosen: list[IdSwitchCandidate] = []
    used_old: set[int] = set()
    used_new: set[int] = set()
    for pair in sorted(pairs, key=lambda c: c.distance_in_heights):
        if pair.old_id in used_old or pair.new_id in used_new:
            continue
        used_old.add(pair.old_id)
        used_new.add(pair.new_id)
        chosen.append(pair)
    return tuple(sorted(chosen, key=lambda c: c.start_frame))
