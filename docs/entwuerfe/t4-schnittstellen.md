# T4: Schnittstellen-Vertrag (für Tests und Umsetzung)

Stand 18.11.2026. Grundlage: `t4-spezifikation.md` Abschnitt 0 (Beschlüsse). Namen im Code englisch.

## domain/
`domain/tracking.py`
```python
@dataclass(frozen=True)
class FrameDetections:
    frame: int                          # Bildindex im Clip (0-basiert)
    detections: tuple[Detection, ...]   # Detection aus domain/detection.py

@dataclass(frozen=True)
class TrackPoint:
    frame: int
    x: float; y: float; w: float; h: float   # Box in Pixeln, x/y = linke obere Ecke
    visible: bool                 # True = vom Detektor gesehen, False = vom Tracker überbrückt
    score: float | None           # Detektor-Score; None, wenn nicht gesehen
    uncertainty: float | None = None  # Platzhalter für T6, in T4 immer None

@dataclass(frozen=True)
class Track:
    id: int
    points: tuple[TrackPoint, ...]   # nach frame aufsteigend, ohne Lücken zwischen erstem und letztem Punkt

DETECTIONS_SCHEMA_VERSION = 1

@dataclass(frozen=True)
class DetectionsDoc:                 # Inhalt von detections.json
    source: str                      # Dateiname des Videos
    detector: str                    # z. B. "rfdetr-small-whole"
    fps: float
    frame_count: int
    frame_size: tuple[int, int]      # (Breite, Höhe)
    stage_params: dict[str, Any]     # Parameter, die das Ergebnis bestimmen (Cache-Schlüssel)
    versions: dict[str, str]         # Bibliotheks-/Modellversionen
    frames: tuple[FrameDetections, ...]
    schema_version: int = DETECTIONS_SCHEMA_VERSION
```
`domain/result.py`: `SCHEMA_VERSION = 2`; `RunResult` bekommt `tracks: tuple[Track, ...] = ()`, `fps: float | None = None`, `frame_count: int | None = None`, `versions: dict[str, str] = {}`. `run --out` schreibt weiterhin ein gültiges (leeres) Ergebnis, jetzt Version 2.

`domain/settings.py`: neu `detect_min_score=0.1`, `track_high_score=0.5`, `track_match_iou=0.3`, `track_max_lost_seconds=1.5`, `track_min_hits=2`, `track_edge_margin_px=40` (auch in `default.toml`, mit Prüfungen in `__post_init__`).

## application/
`application/tracker.py`
```python
class Tracker(Protocol):
    def track(self, frames: Sequence[FrameDetections], frame_count: int,
              frame_size: tuple[int, int]) -> list[Track]: ...

class ByteTrackLikeTracker:
    def __init__(self, settings: Settings, fps: float) -> None: ...
```
Verhalten (jede Zeile ein Test):
1. Gleichmäßig bewegte Person, auf jedem N-ten Bild erkannt: eine ID über 60 s.
2. Lücke kürzer als `track_max_lost_seconds`: ID bleibt.
3. Lücke länger: Spur endet; spätere Erkennungen dort bekommen eine neue ID.
4. Zwei Personen kreuzen sich bei gleichmäßiger Bewegung: IDs bleiben.
5. Score in `[detect_min_score, track_high_score)` verlängert eine Spur, eröffnet aber keine.
6. Erst ab `track_min_hits` Treffern bestätigt; Einzel-Fehlerkennung erzeugt keine Spur.
7. Ohne Kamerawissen: kleine gemeinsame Verschiebung aller Boxen (innerhalb der Überlappungs-Schwelle) ändert keine ID.
9. Spur verschwindet am Bildrand (innerhalb `track_edge_margin_px`): endet nach dem ersten verpassten Erkennungsbild; wer später dort erscheint, bekommt eine neue ID.
10. IDs werden nie wiederverwendet und steigen.
11. Gleiche Eingabe, gleiche Ausgabe.
Ausgabe-Regeln: Punkte nur vom ersten bis zum letzten Treffer einer Spur. Trefferbilder: `visible=True`, Box und Score der Erkennung. Bilder dazwischen: linear interpoliert, `visible=False`, `score=None`. Nur bestätigte Spuren. `uncertainty` immer `None`.

`application/tracking_stages.py`
```python
class FrameSource(Protocol):
    fps: float
    frame_count: int
    frame_size: tuple[int, int]
    name: str                        # Dateiname
    def frames(self, every: int) -> Iterator[tuple[int, np.ndarray]]: ...  # (Index, RGB) für Index % every == 0

class StageStore(Protocol):
    def load_detections(self) -> DetectionsDoc | None: ...   # None, wenn keine (vollständige) Datei
    def save_detections(self, doc: DetectionsDoc) -> None: ...
    def save_tracks(self, result: RunResult) -> None: ...

def detect_stage(source: FrameSource, detector: Detector, detector_name: str,
                 settings: Settings, store: StageStore,
                 versions: dict[str, str]) -> tuple[DetectionsDoc, bool]:
    """Liefert (Dokument, wiederverwendet?). Wiederverwendet nur, wenn stage_params gleich sind.
    stage_params = {detector, detect_every, detect_min_score, detector_model, tile_size, tile_overlap, nms_iou}.
    Speichert nur Erkennungen mit score >= detect_min_score."""

def track_stage(doc: DetectionsDoc, tracker: Tracker, settings: Settings,
                store: StageStore, versions: dict[str, str]) -> RunResult:
    """Läuft immer neu; speichert tracks.json."""
```
`application/track_summary.py`: `summarize_tracks(result: RunResult) -> dict` mit `track_count`, `tracks_per_minute`, `mean_track_seconds`, `visible_share` (None, wenn keine Spuren).

## infrastructure/
- `video_source.py`: `OpenCvFrameSource(path)` (bildweise, BGR -> RGB).
- `stage_files.py`: `FileStageStore(run_dir)`; JSON lesen/schreiben über Temp-Datei + Umbenennen; falsche `schema_version` -> `ValueError` mit Dateiname und Versionen; `null` bleibt `None`. `result_store.py` bekommt `load_result(path)` (lehnt Version 1 ab).
- `track_render.py`: Zählvideo (Box + ID, halbe Geschwindigkeit) und Kontaktbögen alle 2 s.
- `tracking_job.py`: `run_track_job(...)` verdrahtet Bibliothek, Lauf, Detektor (`build_detector(variant, settings)`), Stufen, Darstellung, `summary.json`.

## cli
`matchstats track --game G --clip C [--variant whole|tiles] [--run run-NNN] [--no-render] [--library] [--config]`. Ohne `--run` neuer Lauf.

## Dateien im Lauf-Ordner
`detections.json` (v1), `tracks.json` (v2), `summary.json`, `render/tracks.mp4`, `render/sheet_*.png`.
