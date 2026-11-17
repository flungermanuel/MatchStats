"""Auswahl der Testbilder: gleichmäßig über den Clip verteilt (reine Regeln, keine I/O)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class SampledFrame:
    clip: str  # Dateiname des Videos
    time_s: float  # Zeitpunkt im Video in Sekunden
    frame_number: int  # Bildnummer (ab 0)
    file_name: str  # Name der gespeicherten PNG-Datei


def uniform_timestamps(duration_s: float, count: int) -> list[float]:
    """Teilt den Clip in `count` gleiche Abschnitte und liefert deren Mitten."""
    if count < 1:
        raise ValueError("count muss mindestens 1 sein")
    if duration_s <= 0:
        raise ValueError("duration_s muss größer als 0 sein")
    section = duration_s / count
    return [(i + 0.5) * section for i in range(count)]


def frame_number(time_s: float, fps: float) -> int:
    """Nächstliegende Bildnummer zu einem Zeitpunkt (kaufmännisch gerundet, .5 nach oben)."""
    return int(time_s * fps + 0.5)
