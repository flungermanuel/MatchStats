"""Teamzuordnung nach Trikotfarbe (reines NumPy, deterministisch, kein scikit-learn).

Ablauf: Je Box den Oberkörper ausschneiden, Rasenpixel per HSV-Farbmaske entfernen und die
Medianfarbe (RGB, 0 bis 1) der übrigen Pixel als Merkmal nehmen. Über alle gültigen Boxen werden die
Merkmale mit einem kleinen k-Means (Startpunkte nach "weitester Abstand", keine Zufallszahlen)
gruppiert. Neue Gruppen entstehen nur, wenn ihr Startpunkt mindestens
`team_min_cluster_distance` von den vorhandenen entfernt liegt; so wird eine einzige Trikotfarbe
nicht in zwei "Teams" zerlegt.

Zuordnung der Gruppen:
- Die zwei größten Gruppen sind immer team_a (größere) und team_b, auch wenn eine davon klein ist.
  Gibt es nur eine Farbe, gibt es nur ein Team (team_a).
- Jede weitere Gruppe mit Anteil über `team_outlier_max_share` aller gültigen Boxen ist ein
  größerer Farbzweig eines Teams (z. B. hellere und dunklere Variante desselben Trikots oder
  Licht/Schatten) und wird dem Team zugeschlagen, dessen Gruppenmittelpunkt ihr am nächsten liegt
  (nie unbekannt).
- Nur weitere Gruppen mit Anteil bis `team_outlier_max_share` sind Ausreißer: die größere gilt als
  Schiedsrichter, die kleinere als Torwart; darüber hinaus bleiben Ausreißer unbekannt.
  ANNAHME, SCHWACH: Das ist geraten; Farbe allein trennt Torwart und Schiedsrichter nicht sicher
  (die Messung wählt je Clip die bessere Zuordnung).
- Rauschen: Startpunkte werden nach "weitester Abstand" gewählt, aber nur, wenn sie mindestens
  `team_min_cluster_distance` von den vorhandenen entfernt liegen. Mit `team_cluster_count` = 4
  (zwei Teams, Schiedsrichter, Torwart) bleibt so für echte Ausreißer Platz; gibt es mehr
  Ausreißergruppen als Plätze, fallen die kleinsten (Rauschen) auf "unbekannt".
Konfidenz = Abstand zur zweitnächsten Gruppe geteilt durch die Summe beider Abstände (Heuristik,
keine Wahrscheinlichkeit); bei nur einer Gruppe 1.0.
"""

from collections.abc import Sequence

import numpy as np

from matchstats.domain.detection import HasBox
from matchstats.domain.settings import Settings
from matchstats.domain.teams import TeamPrediction

# Technische Konstanten (keine Einstellungen für den Anwender).
MAX_ITERATIONS = 20
_UNKNOWN = TeamPrediction(label=None, confidence=None)


def _hue_saturation(pixels: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Farbton (0 bis 179, wie OpenCV) und Sättigung (0 bis 255) für RGB-Pixel (N, 3)."""
    rgb = pixels.astype(np.float64)
    maximum = rgb.max(axis=1)
    delta = maximum - rgb.min(axis=1)
    safe_delta = np.where(delta == 0, 1.0, delta)
    r, g, b = rgb[:, 0], rgb[:, 1], rgb[:, 2]
    hue = np.where(
        maximum == r,
        ((g - b) / safe_delta) % 6,
        np.where(maximum == g, (b - r) / safe_delta + 2, (r - g) / safe_delta + 4),
    )
    hue = np.where(delta == 0, 0.0, hue * 30.0)
    saturation = np.where(maximum == 0, 0.0, 255.0 * delta / np.where(maximum == 0, 1.0, maximum))
    return hue, saturation


class ColorTeamClassifier:
    def __init__(self, settings: Settings) -> None:
        self._s = settings
        self._group_sizes: list[int] = []

    def last_group_sizes(self) -> list[int]:
        """Boxenzahl je Farbgruppe des letzten classify-Aufrufs, absteigend."""
        return list(self._group_sizes)

    def classify(
        self, images: Sequence[np.ndarray], boxes: Sequence[HasBox]
    ) -> list[TeamPrediction]:
        if len(images) != len(boxes):
            raise ValueError("images und boxes müssen gleich viele Einträge haben")
        features: list[np.ndarray] = []
        valid: list[int] = []
        for i, (image, box) in enumerate(zip(images, boxes, strict=True)):
            feature = self._feature(image, box)
            if feature is not None:
                features.append(feature)
                valid.append(i)
        result = [_UNKNOWN] * len(boxes)
        self._group_sizes = []
        if not features:
            return result
        for index, prediction in zip(valid, self._assign(np.array(features)), strict=True):
            result[index] = prediction
        return result

    def _feature(self, image: np.ndarray, box: HasBox) -> np.ndarray | None:
        """Medianfarbe der Nicht-Rasen-Pixel im Oberkörper; None, wenn nicht bestimmbar."""
        s = self._s
        if box.h < s.team_min_box_height_px or box.w < s.team_min_box_width_px:
            return None
        height, width = image.shape[:2]
        x0, x1 = max(0, round(box.x)), min(width, round(box.x + box.w))
        y0 = max(0, round(box.y))
        y1 = min(height, round(box.y + box.h * s.team_upper_body_fraction))
        if x1 <= x0 or y1 <= y0:
            return None
        pixels = image[y0:y1, x0:x1].reshape(-1, 3)
        hue, saturation = _hue_saturation(pixels)
        low, high = s.team_grass_hue_range
        grass = (hue >= low) & (hue <= high) & (saturation >= s.team_grass_min_saturation)
        kept = pixels[~grass]
        if len(kept) < s.team_min_pixels:
            return None
        return np.median(kept.astype(np.float64), axis=0) / 255.0

    def _cluster(self, features: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Deterministisches k-Means; liefert (Mittelpunkte, Gruppennummer je Merkmal)."""
        centers = [features[np.argmin(np.linalg.norm(features - features.mean(axis=0), axis=1))]]
        while len(centers) < self._s.team_cluster_count:
            distance = np.min(
                np.linalg.norm(features[:, None] - np.array(centers)[None], axis=2), axis=1
            )
            farthest = int(np.argmax(distance))
            if distance[farthest] < self._s.team_min_cluster_distance:
                break
            centers.append(features[farthest])
        means = np.array(centers)
        assignment = np.zeros(len(features), dtype=int)
        for _ in range(MAX_ITERATIONS):
            distances = np.linalg.norm(features[:, None] - means[None], axis=2)
            assignment = np.argmin(distances, axis=1)
            new_means = np.array(
                [
                    features[assignment == k].mean(axis=0) if np.any(assignment == k) else means[k]
                    for k in range(len(means))
                ]
            )
            if np.allclose(new_means, means):
                break
            means = new_means
        distances = np.linalg.norm(features[:, None] - means[None], axis=2)
        return means, np.argmin(distances, axis=1)

    def _assign(self, features: np.ndarray) -> list[TeamPrediction]:
        means, assignment = self._cluster(features)
        count = len(means)
        sizes = np.bincount(assignment, minlength=count)
        # Größte zuerst; bei Gleichstand nach Mittelpunkt (deterministisch).
        order = sorted(range(count), key=lambda k: (-sizes[k], tuple(means[k])))
        self._group_sizes = sorted((int(s) for s in sizes if s > 0), reverse=True)
        limit = self._s.team_outlier_max_share * len(features)
        class_of: dict[int, str | None] = {k: None for k in range(count)}
        for k, name in zip(order[:2], ("team_a", "team_b"), strict=False):
            class_of[k] = name
        outliers: list[int] = []
        for k in order[2:]:
            if sizes[k] == 0:
                continue
            if sizes[k] > limit:
                # Große weitere Gruppe: nächstgelegenem Team zuschlagen (nie unbekannt).
                team_ks = order[:2]
                nearest = min(team_ks, key=lambda t: float(np.linalg.norm(means[k] - means[t])))
                class_of[k] = class_of[nearest]
            else:
                outliers.append(k)
        for k, name in zip(outliers, ("referee", "goalkeeper"), strict=False):
            class_of[k] = name

        distances = np.linalg.norm(features[:, None] - means[None], axis=2)
        predictions: list[TeamPrediction] = []
        for i, k in enumerate(assignment):
            label = class_of[int(k)]
            if label is None:
                predictions.append(_UNKNOWN)
                continue
            others = np.delete(distances[i], k)
            if others.size == 0:
                confidence = 1.0
            else:
                own, other = float(distances[i, k]), float(others.min())
                confidence = other / (own + other) if own + other > 0 else 1.0
            predictions.append(TeamPrediction(label=label, confidence=confidence))
        return predictions
