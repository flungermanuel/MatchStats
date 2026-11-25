"""Stufe 4: Teamklasse je Spur (teams.json) durch Abstimmung über Stichproben.

Je Spur werden bis zu `team_samples_per_track` gesehene Punkte gewählt. Alle gewählten Boxen eines
Clips gehen in einem einzigen Aufruf an den Klassifikator (er gruppiert über die ganze Menge). Das
Video wird einmal gelesen; je Stichprobe wird nur ein Ausschnitt um die Box gehalten. Kennt nur
Ports, keine Bibliotheken außer NumPy.
"""

import math
from collections.abc import Sequence
from dataclasses import fields, replace
from typing import Any, Protocol

import numpy as np

from matchstats.application.team_classifier import TeamClassifier
from matchstats.application.tracking_stages import FrameSource, _is_reusable
from matchstats.domain.detection import Detection
from matchstats.domain.result import RunResult
from matchstats.domain.settings import Settings
from matchstats.domain.teams import (
    TeamPrediction,
    TeamsDoc,
    select_sample_points,
    tracks_fingerprint,
    vote_track,
)
from matchstats.domain.tracking import TrackPoint

NOTE = (
    "team_a/team_b sind willkürliche Namen je Lauf; Torwart/Schiedsrichter sind über Farbe "
    "unzuverlässig (siehe T5c). Abstimmung über höchstens {n} Stichproben je Spur; "
    "Gruppierung über die Stichproben aller Spuren."
)


class TeamsStore(Protocol):
    def load_teams(self) -> TeamsDoc | None:
        """None, wenn keine (vollständige) Datei vorliegt."""
        ...

    def save_teams(self, doc: TeamsDoc) -> None: ...


def team_params(settings: Settings, classifier_name: str) -> dict[str, Any]:
    """Alles, was teams.json bestimmt (Cache-Schlüssel), JSON-fest (Tupel als Listen)."""
    params: dict[str, Any] = {"classifier": classifier_name}
    for field in fields(settings):
        if field.name.startswith("team_"):
            value = getattr(settings, field.name)
            params[field.name] = list(value) if isinstance(value, tuple) else value
    return params


def crop_box(image: np.ndarray, box: Detection) -> tuple[np.ndarray, Detection]:
    """Ausschnitt um die ganze Box (auf die Bildgrenzen gekürzt) und die verschobene Box.

    Der Ursprung ist ganzzahlig und gerade: Verschieben um eine gerade Zahl ändert weder das
    Runden auf ganze Pixel noch dessen Gleichstandsregel, also sind die Vorhersagen des
    Klassifikators auf dem Ausschnitt identisch zu denen auf dem Ganzbild.
    """
    height, width = image.shape[:2]
    x0 = max(0, math.floor(box.x))
    y0 = max(0, math.floor(box.y))
    x0 -= x0 % 2
    y0 -= y0 % 2
    x1 = min(width, max(x0, math.ceil(box.x + box.w)))
    y1 = min(height, max(y0, math.ceil(box.y + box.h)))
    # Kopie statt View: Eine View hielte das ganze Videobild im Speicher.
    return image[y0:y1, x0:x1].copy(), replace(box, x=box.x - x0, y=box.y - y0)


def team_stage(
    result: RunResult,
    source: FrameSource,
    classifier: TeamClassifier,
    classifier_name: str,
    settings: Settings,
    store: TeamsStore,
    versions: dict[str, str],
) -> tuple[TeamsDoc, bool]:
    """Teamklasse je Spur. Liefert (Dokument, wiederverwendet?).

    Wiederverwendet wird nur bei gleichen stage_params (inkl. Klassifikatorname), gleichem Video
    und gleichem Spur-Fingerabdruck; dann wird das Video nicht gelesen.
    """
    if result.source != source.name or result.frame_count != source.frame_count:
        raise ValueError(
            f"Spuren gehören zu {result.source!r} ({result.frame_count} Bilder), "
            f"das Video ist {source.name!r} ({source.frame_count} Bilder)"
        )
    params = team_params(settings, classifier_name)
    fingerprint = tracks_fingerprint(result.tracks)
    existing = store.load_teams()
    if (
        existing is not None
        and _is_reusable(existing, source, params)
        and existing.tracks_fingerprint == fingerprint
    ):
        return existing, True

    chosen = [
        select_sample_points(t, settings.team_samples_per_track, settings.team_vote_min_box_height)
        for t in result.tracks
    ]
    predictions = _classify_samples(chosen, source, classifier)
    doc = TeamsDoc(
        source=source.name,
        fps=source.fps,
        frame_count=source.frame_count,
        frame_size=source.frame_size,
        stage_params=params,
        tracks_fingerprint=fingerprint,
        versions=versions,
        note=NOTE.format(n=settings.team_samples_per_track),
        tracks=tuple(
            vote_track(track.id, predictions[i], settings.team_min_votes)
            for i, track in enumerate(result.tracks)
        ),
    )
    store.save_teams(doc)
    return doc, False


def _classify_samples(
    chosen: Sequence[Sequence[TrackPoint]], source: FrameSource, classifier: TeamClassifier
) -> list[list[TeamPrediction]]:
    """Ein classify-Aufruf für alle Stichproben; Vorhersagen je Spur in Spurreihenfolge."""
    wanted: dict[int, list[tuple[int, TrackPoint]]] = {}  # Bildindex -> [(Spurnummer, Punkt)]
    for track_index, points in enumerate(chosen):
        for point in points:
            wanted.setdefault(point.frame, []).append((track_index, point))
    per_track: list[list[TeamPrediction]] = [[] for _ in chosen]
    if not wanted:
        return per_track

    step = max(1, math.gcd(*wanted))
    last = max(wanted)
    owners: list[int] = []
    images: list[np.ndarray] = []
    boxes: list[Detection] = []
    for index, image in source.frames(step):
        for track_index, p in wanted.get(index, ()):
            crop, box = crop_box(image, Detection(p.x, p.y, p.w, p.h, p.score or 0.0))
            owners.append(track_index)
            images.append(crop)
            boxes.append(box)
        if index >= last:
            break
    for owner, prediction in zip(owners, classifier.classify(images, boxes), strict=True):
        per_track[owner].append(prediction)
    return per_track
