"""RF-DETR (Apache 2.0) als Personen-Detektor. Nur hier darf `rfdetr` importiert werden."""

import numpy as np

from matchstats.domain.detection import Detection

_SIZES = {"nano": "RFDETRNano", "small": "RFDETRSmall", "medium": "RFDETRMedium"}


class RfDetrDetector:
    """Erfüllt den Port `Detector`; die Gewichte (COCO) werden beim ersten Start geladen."""

    def __init__(self, size: str = "small", score_threshold: float = 0.3) -> None:
        if size not in _SIZES:
            raise ValueError(f"Unbekannte Modellgröße {size!r}, erlaubt: {sorted(_SIZES)}")
        import rfdetr  # noch hier, damit der Import (torch) nur bei echter Nutzung passiert
        from rfdetr.assets.coco_classes import COCO_CLASSES

        self._model = getattr(rfdetr, _SIZES[size])()
        self._threshold = score_threshold
        self._person_id = next(k for k, name in COCO_CLASSES.items() if name == "person")

    def detect(self, image: np.ndarray) -> list[Detection]:
        result = self._model.predict(image, threshold=self._threshold)
        found = []
        for (x1, y1, x2, y2), score, cls in zip(
            result.xyxy, result.confidence, result.class_id, strict=True
        ):
            if int(cls) == self._person_id:
                found.append(
                    Detection(float(x1), float(y1), float(x2 - x1), float(y2 - y1), float(score))
                )
        return found
