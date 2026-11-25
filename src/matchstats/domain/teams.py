"""Teamzuordnung (T5a), rein: Vorhersage, Verwechslungstabelle, beste A/B-Zuordnung, Trefferquote.

Zeilen der Tabelle = wahre Klasse, Spalten = vorhergesagte Klasse plus `UNKNOWN`.
Welches Team "A" heißt, ist beim Farbverfahren willkürlich; darum wird vor der Trefferquote die
bessere der zwei Zuordnungen (A=A, B=B oder getauscht) gewählt.
Ebenso werden Torwart und Schiedsrichter getauscht, falls das besser passt.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from matchstats.domain.testset import CLASSES

UNKNOWN = "unbekannt"

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
