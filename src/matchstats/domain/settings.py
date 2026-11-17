"""Parameter der Verarbeitung (kommen aus der Konfiguration, nie fest im Code)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # Erkennung läuft nur auf jedem N-ten Bild, das Tracking überbrückt die Lücken.
    detect_every: int = 5
    # Anzahl Testbilder, die pro Clip gleichmäßig gezogen werden.
    frames_per_clip: int = 20

    def __post_init__(self) -> None:
        if self.detect_every < 1:
            raise ValueError("detect_every muss mindestens 1 sein")
        if self.frames_per_clip < 1:
            raise ValueError("frames_per_clip muss mindestens 1 sein")
