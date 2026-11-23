"""Kamerabewegung mit OpenCV schätzen (Merkmalspunkte, optischer Fluss, RANSAC).

Je Bildpaar: Ecken im vorigen Bild suchen (goodFeaturesToTrack), ins aktuelle Bild verfolgen
(Lucas-Kanade-Fluss) und daraus per RANSAC eine Ähnlichkeitstransformation schätzen
(Verschiebung, Drehung, gleichmäßiger Zoom). Es liegt immer nur ein Bildpaar im Speicher.

Qualität = Anteil der Punkte, die zur geschätzten Bewegung passen (RANSAC-Inlier), geteilt durch
alle erfolgreich verfolgten Punkte. Viele Ausreißer (z. B. bewegte Spieler, Unschärfe) senken sie.
Unter `camera_min_quality`, bei zu wenigen Punkten oder bei Fehlschlag ist die Matrix None
(unbekannt, nicht "keine Bewegung").
"""

from collections.abc import Iterable

import cv2
import numpy as np

from matchstats.domain.camera import CameraMotion, Matrix
from matchstats.domain.settings import Settings

# Technische Konstanten der Schätzung (keine Einstellungen für den Anwender).
MIN_TRACKED_POINTS = 6  # weniger verfolgte Punkte: Schätzung nicht belastbar
CORNER_QUALITY = 0.01
CORNER_MIN_DISTANCE = 8
RANSAC_THRESHOLD_PX = 3.0  # in Pixeln des verkleinerten Bildes


class OpenCvCameraMotionEstimator:
    def __init__(self, settings: Settings) -> None:
        self._downscale = settings.camera_downscale
        self._min_quality = settings.camera_min_quality
        self._max_features = settings.camera_max_features

    def estimate(self, images: Iterable[tuple[int, np.ndarray]]) -> list[CameraMotion]:
        motions: list[CameraMotion] = []
        previous: np.ndarray | None = None
        for index, image in images:
            gray = self._prepare(image)
            if previous is not None:
                motions.append(self._estimate_pair(index, previous, gray))
            previous = gray
        return motions

    def _prepare(self, image: np.ndarray) -> np.ndarray:
        """Graubild, ggf. verkleinert (schneller und rauschärmer)."""
        gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
        if self._downscale < 1.0:
            gray = cv2.resize(
                gray, None, fx=self._downscale, fy=self._downscale, interpolation=cv2.INTER_AREA
            )
        return gray

    def _estimate_pair(self, index: int, previous: np.ndarray, current: np.ndarray) -> CameraMotion:
        unknown = CameraMotion(index, None, None)
        corners = cv2.goodFeaturesToTrack(
            previous,
            maxCorners=self._max_features,
            qualityLevel=CORNER_QUALITY,
            minDistance=CORNER_MIN_DISTANCE,
        )
        if corners is None or len(corners) < MIN_TRACKED_POINTS:
            return unknown
        moved, status, _ = cv2.calcOpticalFlowPyrLK(previous, current, corners, None)
        if moved is None or status is None:
            return unknown
        found = status.ravel() == 1
        if int(found.sum()) < MIN_TRACKED_POINTS:
            return unknown
        matrix, inliers = cv2.estimateAffinePartial2D(
            corners[found],
            moved[found],
            method=cv2.RANSAC,
            ransacReprojThreshold=RANSAC_THRESHOLD_PX,
        )
        if matrix is None or inliers is None:
            return unknown
        quality = float(inliers.sum()) / int(found.sum())
        if quality < self._min_quality:
            return CameraMotion(index, None, quality)
        return CameraMotion(index, self._to_full_resolution(matrix), quality)

    def _to_full_resolution(self, matrix: np.ndarray) -> Matrix:
        """Verschiebung vom verkleinerten ins volle Bild umrechnen (a, b, c, d bleiben gleich)."""
        m = matrix.astype(float)
        tx, ty = m[0, 2] / self._downscale, m[1, 2] / self._downscale
        return (
            (float(m[0, 0]), float(m[0, 1]), float(tx)),
            (float(m[1, 0]), float(m[1, 1]), float(ty)),
        )
