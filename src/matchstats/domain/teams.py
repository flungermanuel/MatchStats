"""Teamzuordnung (T5a), rein: Vorhersage, Verwechslungstabelle, beste A/B-Zuordnung, Trefferquote.

Zeilen der Tabelle = wahre Klasse, Spalten = vorhergesagte Klasse plus `UNKNOWN`.
Welches Team "A" heißt, ist beim Farbverfahren willkürlich; darum wird vor der Trefferquote die
bessere der zwei Zuordnungen (A=A, B=B oder getauscht) gewählt.
Ebenso werden Torwart und Schiedsrichter getauscht, falls das besser passt.
"""

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from matchstats.domain.testset import CLASSES
from matchstats.domain.tracking import Track, TrackPoint

UNKNOWN = "unbekannt"

# Wird erhöht, sobald sich das Format von teams.json ändert.
TEAMS_SCHEMA_VERSION = 1

Table = dict[str, dict[str, int]]


@dataclass(frozen=True)
class TeamPrediction:
    # None = unbekannt (nicht "irgendein Team"); confidence ist dann ebenfalls None.
    label: str | None
    confidence: float | None  # 0 bis 1


def _empty_table() -> Table:
    return {truth: {column: 0 for column in (*CLASSES, UNKNOWN)} for truth in CLASSES}


def confusion_table(truth: Sequence[str], predicted: Sequence[str | None]) -> Table:
    """Zählt je Box (wahre Klasse, Vorhersage); Vorhersage None landet in der Spalte UNKNOWN."""
    if len(truth) != len(predicted):
        raise ValueError("truth und predicted müssen gleich lang sein")
    table = _empty_table()
    for true_label, predicted_label in zip(truth, predicted, strict=True):
        table[true_label][UNKNOWN if predicted_label is None else predicted_label] += 1
    return table


def confusion_near_far(
    heights: Sequence[float],
    truth: Sequence[str],
    predicted: Sequence[str | None],
    limit: float,
) -> tuple[Table, Table]:
    """Zwei Tabellen: nah (Höhe >= limit) und fern (Höhe < limit)."""
    if not len(heights) == len(truth) == len(predicted):
        raise ValueError("heights, truth und predicted müssen gleich lang sein")
    near = [i for i, h in enumerate(heights) if h >= limit]
    far = [i for i, h in enumerate(heights) if h < limit]
    return (
        confusion_table([truth[i] for i in near], [predicted[i] for i in near]),
        confusion_table([truth[i] for i in far], [predicted[i] for i in far]),
    )


def unknown_count(table: Table) -> int:
    return sum(row[UNKNOWN] for row in table.values())


def _correct(table: Table, truth: str, mapping: Mapping[str, str]) -> int:
    row = table[truth]
    return sum(row[p] for p in CLASSES if mapping[p] == truth)


def _hits(table: Table, mapping: Mapping[str, str]) -> int:
    return sum(_correct(table, t, mapping) for t in CLASSES)


def best_team_mapping(table: Table) -> dict[str, str]:
    """Schlüssel = vorhergesagte Klasse, Wert = Klasse, als die sie gezählt wird.

    Team A/B und Torwart/Schiedsrichter werden unabhängig voneinander getauscht, wenn das mehr
    Treffer gibt (bei Gleichstand Identität).
    """
    mapping = {c: c for c in CLASSES}
    for first, second in (("team_a", "team_b"), ("goalkeeper", "referee")):
        swapped = {**mapping, first: second, second: first}
        if _hits(table, swapped) > _hits(table, mapping):
            mapping = swapped
    return mapping


def accuracy(table: Table) -> float | None:
    """Anteil richtiger Boxen nach bester Zuordnung; unbekannt zählt als falsch. None ohne Boxen."""
    total = sum(sum(row.values()) for row in table.values())
    if total == 0:
        return None
    mapping = best_team_mapping(table)
    return sum(_correct(table, t, mapping) for t in CLASSES) / total


def accuracy_per_class(table: Table) -> dict[str, float | None]:
    """Trefferquote je wahrer Klasse (gleiche Zuordnung wie `accuracy`); None ohne Beschriftung."""
    mapping = best_team_mapping(table)
    result: dict[str, float | None] = {}
    for truth in CLASSES:
        total = sum(table[truth].values())
        result[truth] = _correct(table, truth, mapping) / total if total else None
    return result


# --- Teams je Spur (T5b1) -----------------------------------------------------------------


@dataclass(frozen=True)
class TrackTeam:
    id: int
    label: str | None  # None = nicht bestimmbar (zu wenige bekannte Stimmen)
    uncertainty: float | None  # 1 - Anteil der Siegerklasse an den bekannten Stimmen
    samples: int  # Anzahl klassifizierter Stichproben-Boxen
    votes: dict[str, int]  # Klasse -> Anzahl, plus UNKNOWN


@dataclass(frozen=True)
class TeamsDoc:
    """Inhalt von teams.json."""

    source: str
    fps: float
    frame_count: int
    frame_size: tuple[int, int]  # (Breite, Höhe)
    stage_params: dict[str, Any]  # Cache-Schlüssel (alle team_* plus Klassifikatorname)
    tracks_fingerprint: str  # Fingerabdruck der Spuren, aus denen das Dokument entstand
    versions: dict[str, str]
    note: str
    tracks: tuple[TrackTeam, ...]
    schema_version: int = TEAMS_SCHEMA_VERSION


def select_sample_points(track: Track, count: int) -> tuple[TrackPoint, ...]:
    """Bis zu `count` gesehene Punkte, gleichmäßig über die gesehenen Punkte verteilt.

    Erster und letzter gesehener Punkt sind dabei (bei count 1 der mittlere). Deterministisch,
    ohne Doppelte; gerundet wird ganzzahlig (halb auf), damit die Wahl nicht von Gleitkomma abhängt.
    """
    seen = [p for p in track.points if p.visible]
    n = len(seen)
    if n <= count:
        return tuple(seen)
    gaps = count - 1
    if gaps == 0:
        return (seen[(n - 1) // 2],)
    return tuple(seen[(2 * i * (n - 1) + gaps) // (2 * gaps)] for i in range(count))


def vote_track(track_id: int, predictions: Sequence[TeamPrediction], min_votes: int) -> TrackTeam:
    """Abstimmung über die Stichproben einer Spur.

    Unbekannt wird gezählt, stimmt aber für keine Klasse mit. Gleichstand entscheidet die
    Reihenfolge in CLASSES. Ohne `min_votes` bekannte Stimmen ist die Klasse None; die
    Unsicherheit wird trotzdem berechnet, sobald es bekannte Stimmen gibt.
    """
    votes = {name: 0 for name in (*CLASSES, UNKNOWN)}
    for prediction in predictions:
        votes[UNKNOWN if prediction.label is None else prediction.label] += 1
    known = sum(votes[name] for name in CLASSES)
    if known == 0:
        return TrackTeam(track_id, None, None, len(predictions), votes)
    winner = max(CLASSES, key=lambda name: (votes[name], -CLASSES.index(name)))
    uncertainty = 1 - votes[winner] / known
    label = winner if known >= min_votes else None
    return TrackTeam(track_id, label, uncertainty, len(predictions), votes)


def tracks_fingerprint(tracks: Sequence[Track]) -> str:
    """sha256 über id, frame, x, y, w, h und visible aller Punkte (auf 2 Stellen gerundet).

    Unabhängig von der Spurreihenfolge; Score und Unsicherheit zählen nicht.
    """
    rows = [
        [
            track.id,
            [
                [p.frame, round(p.x, 2), round(p.y, 2), round(p.w, 2), round(p.h, 2), p.visible]
                for p in track.points
            ],
        ]
        for track in sorted(tracks, key=lambda t: t.id)
    ]
    return hashlib.sha256(json.dumps(rows, separators=(",", ":")).encode("utf-8")).hexdigest()


def class_change_share(teams: Sequence[TrackTeam]) -> float | None:
    """Anteil der Spuren mit Klasse, die mindestens eine bekannte Stimme für eine andere Klasse
    haben. None ohne Spur mit Klasse."""
    labelled = [t for t in teams if t.label is not None]
    if not labelled:
        return None
    changed = sum(1 for t in labelled if any(t.votes[c] > 0 for c in CLASSES if c != t.label))
    return changed / len(labelled)


def null_track_count(teams: Sequence[TrackTeam]) -> int:
    return sum(1 for t in teams if t.label is None)
