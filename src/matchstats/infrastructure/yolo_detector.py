"""Ultralytics YOLO (AGPL-3.0) als optionaler Personen-Detektor. Nur hier darf `ultralytics`
importiert werden; das Paket ist eine optionale Zusatzabhängigkeit (`pip install -e ".[yolo]"`)."""

import numpy as np

from matchstats.domain.detection import Detection

_WEIGHTS = {"nano": "yolo11n.pt", "small": "yolo11s.pt", "medium": "yolo11m.pt"}
_PERSON_CLASS = 0  # COCO, 0-basiert bei YOLO


class YoloDetector:
    """Erfüllt den Port `Detector`; Gewichte werden beim ersten Start geladen."""

    def __init__(self, size: str = "small", score_threshold: float = 0.3) -> None:
        if size not in _WEIGHTS:
            raise ValueError(f"Unbekannte Modellgröße {size!r}, erlaubt: {sorted(_WEIGHTS)}")
        from ultralytics import YOLO

        self._model = YOLO(_WEIGHTS[size])
        self._threshold = score_threshold

    def detect(self, image: np.ndarray) -> list[Detection]:
        bgr = np.ascontiguousarray(image[:, :, ::-1])  # Ultralytics erwartet BGR-Arrays
        result = self._model.predict(
            bgr, conf=self._threshold, classes=[_PERSON_CLASS], verbose=False
        )[0]
        boxes = result.boxes
        return [
            Detection(float(x1), float(y1), float(x2 - x1), float(y2 - y1), float(score))
            for (x1, y1, x2, y2), score in zip(
                boxes.xyxy.cpu().numpy(), boxes.conf.cpu().numpy(), strict=True
            )
        ]
