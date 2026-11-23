"""Parameter der Verarbeitung (kommen aus der Konfiguration, nie fest im Code)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Erkennung läuft nur auf jedem N-ten Bild, das Tracking überbrückt die Lücken.
    detect_every: int = 5
    # Anzahl Testbilder, die pro Clip gleichmäßig gezogen werden.
    frames_per_clip: int = 20
    # Erkennung (T3): Modellgröße ("nano", "small", "medium"), Mindest-Score einer Erkennung.
    detector_model: str = "small"
    score_threshold: float = 0.3
    # Kachel-Variante: Kantenlänge in Pixeln, Überlappungsanteil, IoU-Schwelle fürs Zusammenführen.
    tile_size: int = 640
    tile_overlap: float = 0.2
    nms_iou: float = 0.5
    # Tracking (T4): Erkennungen unter detect_min_score werden verworfen; ab track_high_score
    # darf eine Erkennung eine Spur eröffnen. Zuordnung per IoU (track_match_iou).
    detect_min_score: float = 0.1
    track_high_score: float = 0.4
    track_match_iou: float = 0.3
    track_max_lost_seconds: float = 1.5
    track_min_hits: int = 3
    track_edge_margin_px: int = 40
    # Kandidaten für ID-Wechsel (T4): neue Spur beginnt höchstens so viele Sekunden nach dem Ende
    # einer alten und höchstens so viele Boxhöhen von deren letzter Position entfernt.
    switch_max_gap_seconds: float = 1.0
    switch_max_distance_heights: float = 1.0
    # Kamerabewegung (T4b): Ausgleich an/aus (kommt normalerweise aus dem Aufnahme-Profil),
    # Verkleinerung des Bildes für die Schätzung, Mindestqualität einer Schätzung (darunter gilt
    # sie als unbekannt) und höchste Zahl verfolgter Merkmalspunkte.
    camera_compensation: bool = True
    camera_downscale: float = 0.5
    camera_min_quality: float = 0.5
    camera_max_features: int = 300

    def __post_init__(self) -> None:
        if self.detect_every < 1:
            raise ValueError("detect_every muss mindestens 1 sein")
        if self.frames_per_clip < 1:
            raise ValueError("frames_per_clip muss mindestens 1 sein")
        if not 0 <= self.score_threshold <= 1:
            raise ValueError("score_threshold muss zwischen 0 und 1 liegen")
        if self.tile_size < 1:
            raise ValueError("tile_size muss mindestens 1 sein")
        if not 0 <= self.tile_overlap < 1:
            raise ValueError("tile_overlap muss in [0, 1) liegen")
        if not 0 <= self.nms_iou <= 1:
            raise ValueError("nms_iou muss zwischen 0 und 1 liegen")
        for name in ("detect_min_score", "track_high_score", "track_match_iou"):
            if not 0 <= getattr(self, name) <= 1:
                raise ValueError(f"{name} muss zwischen 0 und 1 liegen")
        if self.track_max_lost_seconds < 0:
            raise ValueError("track_max_lost_seconds darf nicht negativ sein")
        if self.track_min_hits < 1:
            raise ValueError("track_min_hits muss mindestens 1 sein")
        if self.track_edge_margin_px < 0:
            raise ValueError("track_edge_margin_px darf nicht negativ sein")
        if self.switch_max_gap_seconds < 0:
            raise ValueError("switch_max_gap_seconds darf nicht negativ sein")
        if self.switch_max_distance_heights < 0:
            raise ValueError("switch_max_distance_heights darf nicht negativ sein")
        if not 0 < self.camera_downscale <= 1:
            raise ValueError("camera_downscale muss in (0, 1] liegen")
        if not 0 <= self.camera_min_quality <= 1:
            raise ValueError("camera_min_quality muss zwischen 0 und 1 liegen")
        if self.camera_max_features < 1:
            raise ValueError("camera_max_features muss mindestens 1 sein")
