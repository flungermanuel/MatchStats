"""Pipeline: orchestriert die Stufen. In T1 gibt es noch keine Stufen, nur ein leeres Ergebnis."""

from dataclasses import asdict

from matchstats.domain.result import RunResult
from matchstats.domain.settings import Settings


def run_pipeline(video_name: str, settings: Settings) -> RunResult:
    """Verarbeitet ein Video und liefert das Ergebnis (noch ohne Spuren)."""
    return RunResult(source=video_name, settings=asdict(settings))
