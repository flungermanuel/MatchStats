"""Auswertungsstufe T5a: misst die Teamzuordnung je Clip.

Jeder Clip wird in einem eigenen Aufruf klassifiziert, weil "team_a" je Clip eine andere Farbe
bedeuten kann. Je Clip wird die bessere A/B-Zuordnung gewählt (Identität oder Tausch); danach
werden die Vorhersagen zurückgetauscht und zu einer Gesamttabelle zusammengezählt.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from statistics import median

import numpy as np

from matchstats.application.team_classifier import TeamClassifier
from matchstats.domain.teams import (
    Table,
    TeamPrediction,
    best_team_mapping,
    confusion_near_far,
    confusion_table,
)
from matchstats.domain.testset import LabeledImage


@dataclass(frozen=True)
class TeamEvaluationRun:
    """Ergebnis der Teammessung (alle Vorhersagen sind schon nach der Clip-Zuordnung getauscht)."""

    near_far_height: float | None  # Median der Boxhöhen; None ohne Boxen
    confusion: Table
    confusion_near: Table
    confusion_far: Table
    clip_mappings: dict[str, dict[str, str]]  # Clip -> (vorhergesagt -> gezählt als)
    predictions: dict[str, list[TeamPrediction]]  # je Bildschlüssel, in Reihenfolge der Boxen
    clip_groups: dict[str, list[int]] = field(default_factory=dict)  # Clip -> Gruppengrößen


def _clip_of(key: str) -> str:
    return key.split("/", 1)[0]


def _group_by_clip(images: list[LabeledImage]) -> dict[str, list[LabeledImage]]:
    groups: dict[str, list[LabeledImage]] = {}
    for image in images:
        groups.setdefault(_clip_of(image.file_name), []).append(image)
    return groups


def _classify_clip(
    classifier: TeamClassifier,
    clip_images: list[LabeledImage],
    load_image: Callable[[str], np.ndarray],
) -> tuple[dict[str, str], dict[str, list[TeamPrediction]]]:
    """Ein Aufruf für alle Boxen des Clips; liefert Zuordnung und zurückgetauschte Vorhersagen."""
    pixels, boxes, truth = [], [], []
    for image in clip_images:
        if not image.boxes:
            continue
        array = load_image(image.file_name)
        for box in image.boxes:
            pixels.append(array)
            boxes.append(box)
            truth.append(box.label)
    raw = classifier.classify(pixels, boxes) if boxes else []
    mapping = best_team_mapping(confusion_table(truth, [p.label for p in raw]))

    predictions: dict[str, list[TeamPrediction]] = {}
    position = 0
    for image in clip_images:
        mapped = []
        for _ in image.boxes:
            p = raw[position]
            position += 1
            mapped.append(p if p.label is None else TeamPrediction(mapping[p.label], p.confidence))
        predictions[image.file_name] = mapped
    return mapping, predictions


def evaluate_teams(
    classifier: TeamClassifier,
    images: list[LabeledImage],
    load_image: Callable[[str], np.ndarray],
) -> TeamEvaluationRun:
    """Misst die Teamzuordnung; Bildschlüssel haben die Form "<clip>/<datei>"."""
    clip_mappings: dict[str, dict[str, str]] = {}
    predictions: dict[str, list[TeamPrediction]] = {}
    clip_groups: dict[str, list[int]] = {}
    group_sizes = getattr(classifier, "last_group_sizes", None)  # nur der Farbklassifikator
    for clip, clip_images in _group_by_clip(images).items():
        clip_mappings[clip], clip_predictions = _classify_clip(classifier, clip_images, load_image)
        predictions.update(clip_predictions)
        clip_groups[clip] = list(group_sizes()) if callable(group_sizes) else []

    heights = [b.h for image in images for b in image.boxes]
    truth = [b.label for image in images for b in image.boxes]
    predicted = [p.label for image in images for p in predictions[image.file_name]]
    limit = float(median(heights)) if heights else None
    if limit is None:
        near, far = confusion_table([], []), confusion_table([], [])
    else:
        near, far = confusion_near_far(heights, truth, predicted, limit)
    return TeamEvaluationRun(
        near_far_height=limit,
        confusion=confusion_table(truth, predicted),
        confusion_near=near,
        confusion_far=far,
        clip_mappings=clip_mappings,
        predictions=predictions,
        clip_groups=clip_groups,
    )


def _has_error(image: LabeledImage, run: TeamEvaluationRun) -> bool:
    predicted = run.predictions.get(image.file_name, [])
    return any(p.label != box.label for box, p in zip(image.boxes, predicted, strict=False))


def select_overlay_keys(
    images: list[LabeledImage], run: TeamEvaluationRun, count: int
) -> list[str]:
    """Bilder mit Fehlern zuerst (unbekannt = Fehler), Rest gleichmäßig verteilt aufgefüllt."""
    wrong = [i.file_name for i in images if _has_error(i, run)]
    wrong_set = set(wrong)
    chosen = wrong[:count]
    rest = [i.file_name for i in images if i.file_name not in wrong_set]
    missing = count - len(chosen)
    if missing > 0 and rest:
        step = max(1, len(rest) // missing)
        chosen += rest[::step][:missing]
    return chosen
