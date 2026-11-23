"""Kamerabewegung: Datentypen und Matrixrechnung (reines Python, ohne Bilder).

Eine Bewegung je Bild f beschreibt, wohin ein Punkt aus Bild f-1 in Bild f wandert
(Ähnlichkeitstransformation als 2x3-Matrix: Verschiebung, Drehung, gleichmäßiger Zoom).
Fehlt eine Schätzung, steht `matrix = None` (unbekannt, nicht "keine Bewegung").
"""

import math
from dataclasses import dataclass, field
from typing import Any

# Zeile 0 und 1 einer affinen 2x3-Matrix: (a, b, tx), (c, d, ty); x' = a*x + b*y + tx.
Matrix = tuple[tuple[float, float, float], tuple[float, float, float]]

IDENTITY: Matrix = ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0))

# Wird erhöht, sobald sich das Format von camera.json ändert.
CAMERA_SCHEMA_VERSION = 1


def compose(first: Matrix, second: Matrix) -> Matrix:
    """Erst `first`, dann `second` anwenden (ergibt wieder eine 2x3-Matrix)."""
    (a1, b1, t1), (c1, d1, u1) = first
    (a2, b2, t2), (c2, d2, u2) = second
    return (
        (a2 * a1 + b2 * c1, a2 * b1 + b2 * d1, a2 * t1 + b2 * u1 + t2),
        (c2 * a1 + d2 * c1, c2 * b1 + d2 * d1, c2 * t1 + d2 * u1 + u2),
    )


def apply_to_box(
    matrix: Matrix, x: float, y: float, w: float, h: float
) -> tuple[float, float, float, float]:
    """Bildet eine Box (x, y = linke obere Ecke) ab: Mitte per Matrix, Größe mit sqrt(|det|)."""
    (a, b, tx), (c, d, ty) = matrix
    cx, cy = x + w / 2, y + h / 2
    new_cx = a * cx + b * cy + tx
    new_cy = c * cx + d * cy + ty
    scale = math.sqrt(abs(a * d - b * c))
    new_w, new_h = w * scale, h * scale
    return new_cx - new_w / 2, new_cy - new_h / 2, new_w, new_h


@dataclass(frozen=True)
class CameraMotion:
    frame: int  # Bildindex f (ab 1): Bewegung von Bild f-1 nach Bild f
    matrix: Matrix | None  # None = Schätzung fehlgeschlagen
    quality: float | None  # 0 bis 1; None, wenn unbekannt


@dataclass(frozen=True)
class CameraPath:
    """Alle Bewegungen eines Clips; verkettet sie zwischen zwei beliebigen Bildern."""

    motions: tuple[CameraMotion, ...] = ()
    # Schnellzugriff Bild -> Bewegung (aus motions abgeleitet, nicht Teil des Vergleichs)
    _by_frame: dict[int, CameraMotion] = field(
        init=False, repr=False, compare=False, default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "_by_frame", {m.frame: m for m in self.motions})

    def transform(self, from_frame: int, to_frame: int) -> Matrix | None:
        """Verkettet die Bewegungen der Bilder from+1 .. to. None, wenn ein Glied unbekannt ist."""
        if to_frame < from_frame:
            raise ValueError(f"to_frame {to_frame} liegt vor from_frame {from_frame}")
        result = IDENTITY
        for frame in range(from_frame + 1, to_frame + 1):
            motion = self._by_frame.get(frame)
            if motion is None or motion.matrix is None:
                return None
            result = compose(result, motion.matrix)
        return result

    def shift_box(
        self, x: float, y: float, w: float, h: float, from_frame: int, to_frame: int
    ) -> tuple[float, float, float, float]:
        """Box von Bild from nach Bild to bringen; bei unbekannter Bewegung unverändert."""
        matrix = self.transform(from_frame, to_frame)
        if matrix is None:
            return x, y, w, h
        return apply_to_box(matrix, x, y, w, h)


NO_CAMERA = CameraPath()


@dataclass(frozen=True)
class CameraDoc:
    """Inhalt von camera.json."""

    source: str  # Dateiname des Videos
    fps: float
    frame_count: int
    frame_size: tuple[int, int]  # (Breite, Höhe)
    stage_params: dict[str, Any]  # Parameter, die das Ergebnis bestimmen (Cache-Schlüssel)
    versions: dict[str, str]
    motions: tuple[CameraMotion, ...]
    schema_version: int = CAMERA_SCHEMA_VERSION

    def path(self) -> CameraPath:
        return CameraPath(motions=self.motions)
