"""Tracker: verbindet Erkennungen über die Zeit zu Spuren (ByteTrack-ähnlich, ohne Kamerawissen).

Es wird nur auf Erkennungsbildern zugeordnet; die Bilder dazwischen werden am Ende linear
interpoliert. Bewegungsmodell: konstante Geschwindigkeit der Boxmitte, Boxgröße = letzte Messung.
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Protocol

import numpy as np
from scipy.optimize import linear_sum_assignment

from matchstats.domain.detection import Detection, iou
from matchstats.domain.settings import Settings
from matchstats.domain.tracking import FrameDetections, Track, TrackPoint

# Anteil des Vorhersagefehlers, der in die Geschwindigkeit einfließt (0 = nie, 1 = ganz).
VELOCITY_GAIN = 0.5


class Tracker(Protocol):
    def track(
        self, frames: Sequence[FrameDetections], frame_count: int, frame_size: tuple[int, int]
    ) -> list[Track]: ...


@dataclass(frozen=True)
class _Box:
    x: float
    y: float
    w: float
    h: float


@dataclass
class _Hit:
    frame: int
    detection: Detection


@dataclass
class _Candidate:
    """Laufende Spur: alle Treffer plus Bewegungszustand."""

    hits: list[_Hit] = field(default_factory=list)
    vx: float = 0.0  # Pixel pro Bild (Boxmitte)
    vy: float = 0.0
    id: int | None = None  # erst nach Bestätigung vergeben

    @property
    def last(self) -> _Hit:
        return self.hits[-1]

    def predict(self, frame: int) -> _Box:
        d = self.last.detection
        dt = frame - self.last.frame
        return _Box(d.x + self.vx * dt, d.y + self.vy * dt, d.w, d.h)

    def update(self, frame: int, det: Detection) -> None:
        previous = self.predict(frame)
        dt = frame - self.last.frame
        if dt > 0:
            # Vorhersagefehler der Boxmitte
            err_x = (det.x + det.w / 2) - (previous.x + previous.w / 2)
            err_y = (det.y + det.h / 2) - (previous.y + previous.h / 2)
            self.vx += VELOCITY_GAIN * err_x / dt
            self.vy += VELOCITY_GAIN * err_y / dt
        self.hits.append(_Hit(frame, det))


class ByteTrackLikeTracker:
    def __init__(self, settings: Settings, fps: float) -> None:
        self._s = settings
        self._max_lost = round(settings.track_max_lost_seconds * fps)

    def track(
        self, frames: Sequence[FrameDetections], frame_count: int, frame_size: tuple[int, int]
    ) -> list[Track]:
        s = self._s
        active: list[_Candidate] = []
        finished: list[_Candidate] = []
        next_id = 1

        for fd in sorted(frames, key=lambda f: f.frame):
            dets = [d for d in fd.detections if d.score >= s.detect_min_score]
            high = [d for d in dets if d.score >= s.track_high_score]
            low = [d for d in dets if d.score < s.track_high_score]

            # Stufe 1: hohe Scores gegen alle aktiven Spuren, Stufe 2: niedrige nur gegen den
            # Rest der bestätigten Spuren (wie klassisches ByteTrack).
            matched1, free_tracks, free_high = self._associate(active, high, fd.frame)
            confirmed_free = [t for t in free_tracks if t.id is not None]
            unconfirmed_free = [t for t in free_tracks if t.id is None]
            matched2, still_free, _ = self._associate(confirmed_free, low, fd.frame)
            free_tracks = still_free + unconfirmed_free
            matched = {id(t) for t, _ in matched1 + matched2}
            for track, det in matched1 + matched2:
                track.update(fd.frame, det)

            survivors = [t for t in active if id(t) in matched]
            for track in free_tracks:
                if self._keeps_waiting(track, fd.frame, frame_size):
                    survivors.append(track)
                else:
                    finished.append(track)

            # Neue Kandidaten nur aus unzugeordneten hohen Scores.
            for det in free_high:
                survivors.append(_Candidate(hits=[_Hit(fd.frame, det)]))
            active = survivors

            for track in active:
                if track.id is None and len(track.hits) >= s.track_min_hits:
                    track.id = next_id
                    next_id += 1

        finished.extend(active)
        confirmed = [t for t in finished if t.id is not None]
        return [_to_track(t) for t in sorted(confirmed, key=lambda t: t.id or 0)]

    def _associate(
        self, tracks: list[_Candidate], dets: list[Detection], frame: int
    ) -> tuple[list[tuple[_Candidate, Detection]], list[_Candidate], list[Detection]]:
        """Ordnet per IoU (ungarische Methode) zu; Rückgabe: Paare, freie Spuren, freie Boxen."""
        if not tracks or not dets:
            return [], list(tracks), list(dets)
        overlap = np.zeros((len(tracks), len(dets)))
        for i, track in enumerate(tracks):
            predicted = track.predict(frame)
            for j, det in enumerate(dets):
                value = iou(predicted, det)
                overlap[i, j] = value if value >= self._s.track_match_iou else 0.0
        rows, cols = linear_sum_assignment(-overlap)
        pairs = [(int(i), int(j)) for i, j in zip(rows, cols, strict=True) if overlap[i, j] > 0]
        used_tracks = {i for i, _ in pairs}
        used_dets = {j for _, j in pairs}
        return (
            [(tracks[i], dets[j]) for i, j in pairs],
            [t for i, t in enumerate(tracks) if i not in used_tracks],
            [d for j, d in enumerate(dets) if j not in used_dets],
        )

    def _keeps_waiting(self, track: _Candidate, frame: int, frame_size: tuple[int, int]) -> bool:
        """Spur ohne Treffer in diesem Bild: weiter überbrücken oder beenden?"""
        if track.id is None:
            return False  # unbestätigter Kandidat: ein Fehlschlag genügt
        if frame - track.last.frame > self._max_lost:
            return False
        return not self._at_edge(track.last.detection, frame_size)

    def _at_edge(self, box: Detection, frame_size: tuple[int, int]) -> bool:
        m = self._s.track_edge_margin_px
        width, height = frame_size
        return box.x <= m or box.y <= m or box.x + box.w >= width - m or box.y + box.h >= height - m


def _to_track(candidate: _Candidate) -> Track:
    """Treffer zu Punkten; Bilder zwischen zwei Treffern linear interpoliert."""
    points: list[TrackPoint] = []
    for hit, nxt in zip(candidate.hits, candidate.hits[1:] + [None], strict=True):
        d = hit.detection
        points.append(TrackPoint(hit.frame, d.x, d.y, d.w, d.h, True, d.score))
        if nxt is None:
            continue
        n = nxt.detection
        span = nxt.frame - hit.frame
        for frame in range(hit.frame + 1, nxt.frame):
            t = (frame - hit.frame) / span
            points.append(
                TrackPoint(
                    frame,
                    d.x + (n.x - d.x) * t,
                    d.y + (n.y - d.y) * t,
                    d.w + (n.w - d.w) * t,
                    d.h + (n.h - d.h) * t,
                    False,
                    None,
                )
            )
    return Track(id=candidate.id or 0, points=tuple(points))
