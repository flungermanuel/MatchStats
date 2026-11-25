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
    # Teamzuordnung (T5a): Anteil der Boxhöhe von oben (Oberkörper), Mindestgröße einer Box,
    # Rasen-Farbmaske (Farbton 0 bis 179 wie OpenCV, Mindest-Sättigung 0 bis 255), Zahl der
    # Farbgruppen, Höchstanteil einer Ausreißergruppe (Torwart/Schiedsrichter), Mindestzahl
    # Nicht-Rasen-Pixel einer Box.
    team_upper_body_fraction: float = 0.5
    team_min_box_height_px: int = 24
    team_min_box_width_px: int = 8
    team_grass_hue_range: tuple[int, int] = (35, 85)
    team_grass_min_saturation: int = 40
    team_cluster_count: int = 4
    team_outlier_max_share: float = 0.15
    team_min_cluster_distance: float = 0.2
    team_min_pixels: int = 30
    # Teams je Spur (T5b1): Stichproben je Spur und Mindestzahl bekannter Stimmen.
    team_samples_per_track: int = 8
    team_min_votes: int = 3

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
        if not 0 < self.team_upper_body_fraction <= 1:
            raise ValueError("team_upper_body_fraction muss in (0, 1] liegen")
        if self.team_min_box_height_px < 1 or self.team_min_box_width_px < 1:
            raise ValueError(
                "team_min_box_height_px und team_min_box_width_px müssen mindestens 1 sein"
            )
        if len(self.team_grass_hue_range) != 2:
            raise ValueError("team_grass_hue_range braucht genau zwei Werte (von, bis)")
        low, high = self.team_grass_hue_range
        if not 0 <= low < high <= 179:
            raise ValueError("team_grass_hue_range muss 0 <= von < bis <= 179 erfüllen")
        if not 0 <= self.team_grass_min_saturation <= 255:
            raise ValueError("team_grass_min_saturation muss zwischen 0 und 255 liegen")
        if self.team_cluster_count < 2:
            raise ValueError("team_cluster_count muss mindestens 2 sein")
        if not 0 < self.team_outlier_max_share < 0.5:
            raise ValueError("team_outlier_max_share muss in (0, 0.5) liegen")
        if self.team_min_cluster_distance <= 0:
            raise ValueError("team_min_cluster_distance muss größer als 0 sein")
        if self.team_min_pixels < 1:
            raise ValueError("team_min_pixels muss mindestens 1 sein")
        if self.team_samples_per_track < 1:
            raise ValueError("team_samples_per_track muss mindestens 1 sein")
        if self.team_min_votes < 1:
            raise ValueError("team_min_votes muss mindestens 1 sein")
