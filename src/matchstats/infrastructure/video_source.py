"""Videoquelle mit OpenCV: liest Bild für Bild, lädt nie das ganze Video."""

import math
from collections.abc import Iterator
from pathlib import Path

import cv2
import numpy as np

# frame_count aus OpenCV kann ungenau sein: so viele fehlende Bilder am Ende sind noch ok.
FRAME_COUNT_TOLERANCE = 2


def _read_fps(capture: cv2.VideoCapture) -> float:
    return float(capture.get(cv2.CAP_PROP_FPS))


class OpenCvFrameSource:
    def __init__(self, path: Path) -> None:
        self._path = Path(path)
        capture = cv2.VideoCapture(str(self._path))
        try:
            if not capture.isOpened():
                raise OSError(f"Video nicht lesbar: {self._path}")
            self.fps = _read_fps(capture)
            if not math.isfinite(self.fps) or self.fps <= 0:
                raise ValueError(f"Ungültige fps ({self.fps}) im Video: {self._path}")
            self.frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
            self.frame_size = (
                int(capture.get(cv2.CAP_PROP_FRAME_WIDTH)),
                int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT)),
            )
        finally:
            capture.release()
        self.name = self._path.name

    def frames(self, every: int) -> Iterator[tuple[int, np.ndarray]]:
        """(Index, RGB-Bild) für jeden Index mit Index % every == 0; ein Bild im Speicher.

        Endet das Dekodieren deutlich vor frame_count, wird ein ValueError geworfen
        (sonst gälte ein halbes Ergebnis als vollständig).
        """
        capture = cv2.VideoCapture(str(self._path))
        try:
            index = 0
            while True:
                if index % every == 0:
                    ok, bgr = capture.read()
                    if not ok:
                        break
                    yield index, cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
                elif not capture.grab():  # überspringen ohne Dekodier-Kopie
                    break
                index += 1
            last_read = index - 1
            if self.frame_count > 0 and last_read < self.frame_count - 1 - FRAME_COUNT_TOLERANCE:
                raise ValueError(
                    f"Video {self.name} nur teilweise lesbar: erwartet {self.frame_count} "
                    f"Bilder, gelesen {last_read + 1}"
                )
        finally:
            capture.release()
