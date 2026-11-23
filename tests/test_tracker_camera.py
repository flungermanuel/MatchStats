"""T4b: Tracker mit Kameraausgleich (künstliche Daten: stehende Personen, Kamera bewegt sich).

Alle Personen stehen in der Welt still; die Kamera schwenkt oder zoomt, daher bewegen sich alle
Boxen im Bild gemeinsam. Mit bekanntem CameraPath bleiben die IDs, ohne reißen sie.
"""

from matchstats.application.tracker import ByteTrackLikeTracker
from matchstats.domain.camera import IDENTITY, NO_CAMERA, CameraMotion, CameraPath
from matchstats.domain.detection import Detection
from matchstats.domain.settings import Settings
from matchstats.domain.tracking import FrameDetections
from test_tracker_rules import BOX_H, BOX_W, EVERY, FPS, FRAME_SIZE, Walker, make_frames

FRAME_COUNT = 205
CENTER = (FRAME_SIZE[0] / 2, FRAME_SIZE[1] / 2)
# Weltpositionen (linke obere Ecke), weit genug auseinander, damit nichts überlappt
PEOPLE = [(400.0, 300.0), (700.0, 500.0), (1000.0, 800.0)]


def _track(frames, camera=None, frame_count=FRAME_COUNT):
    tracker = ByteTrackLikeTracker(Settings(), FPS)
    if camera is None:
        return tracker.track(frames, frame_count, FRAME_SIZE)
    return tracker.track(frames, frame_count, FRAME_SIZE, camera)


def _path(matrix_at, frame_count=FRAME_COUNT) -> CameraPath:
    """Pfad für die Bilder 1 .. frame_count-1; matrix_at(frame) liefert eine Matrix oder None."""
    motions = []
    for frame in range(1, frame_count):
        matrix = matrix_at(frame)
        motions.append(CameraMotion(frame, matrix, None if matrix is None else 1.0))
    return CameraPath(motions=tuple(motions))


# --- Schwenk ---


def _pan_offset(frame: int) -> float:
    """Bildverschiebung in x: 20 px pro Bild in den Bildern 96 bis 100 (zusammen 100 px)."""
    return 20.0 * min(max(frame - 95, 0), 5)


def _pan_matrix(frame):
    return ((1.0, 0.0, 20.0 if 96 <= frame <= 100 else 0.0), (0.0, 1.0, 0.0))


def _pan_frames() -> list[FrameDetections]:
    frames = []
    for frame in range(0, FRAME_COUNT, EVERY):
        dets = tuple(Detection(wx + _pan_offset(frame), wy, BOX_W, BOX_H, 0.9) for wx, wy in PEOPLE)
        frames.append(FrameDetections(frame, dets))
    return frames


def test_tracker_keeps_ids_when_camera_pans():
    tracks = _track(_pan_frames(), _path(_pan_matrix))

    assert len(tracks) == len(PEOPLE)
    assert all(t.points[0].frame == 0 and t.points[-1].frame >= FRAME_COUNT - 10 for t in tracks)


def test_without_camera_compensation_a_pan_breaks_the_ids():
    # Gegenprobe: gleiche Daten ohne Ausgleich -> Spuren reißen (sonst prüft der Test oben nichts)
    tracks = _track(_pan_frames(), NO_CAMERA)

    assert len(tracks) > len(PEOPLE)


# --- Zoom ---

ZOOM = 1.3
ZOOM_PEOPLE = [(1200.0, 300.0), (1500.0, 500.0), (1400.0, 800.0)]


def _zoom_box(frame, wx, wy):
    if frame < 100:
        return Detection(wx, wy, BOX_W, BOX_H, 0.9)
    # Boxmitte um das Bildzentrum skalieren, Größe mit dem Zoomfaktor
    cx = CENTER[0] + (wx + BOX_W / 2 - CENTER[0]) * ZOOM
    cy = CENTER[1] + (wy + BOX_H / 2 - CENTER[1]) * ZOOM
    w, h = BOX_W * ZOOM, BOX_H * ZOOM
    return Detection(cx - w / 2, cy - h / 2, w, h, 0.9)


def _zoom_matrix(frame):
    if frame != 100:
        return IDENTITY
    return ((ZOOM, 0.0, CENTER[0] * (1 - ZOOM)), (0.0, ZOOM, CENTER[1] * (1 - ZOOM)))


def _zoom_frames() -> list[FrameDetections]:
    return [
        FrameDetections(f, tuple(_zoom_box(f, wx, wy) for wx, wy in ZOOM_PEOPLE))
        for f in range(0, FRAME_COUNT, EVERY)
    ]


def test_tracker_keeps_ids_when_camera_zooms():
    tracks = _track(_zoom_frames(), _path(_zoom_matrix))

    assert len(tracks) == len(ZOOM_PEOPLE)
    assert all(t.points[-1].frame >= FRAME_COUNT - 10 for t in tracks)


def test_without_camera_compensation_a_zoom_breaks_the_ids():
    tracks = _track(_zoom_frames(), NO_CAMERA)

    assert len(tracks) > len(ZOOM_PEOPLE)


# --- Geschwindigkeit ---


def _slow_pan_offset(frame: int) -> float:
    """Kamera schwenkt in den Bildern 51 bis 100 mit 4 px pro Bild und steht danach still."""
    return 4.0 * min(max(frame - 50, 0), 50)


def _slow_pan_matrix(frame):
    return ((1.0, 0.0, 4.0 if 51 <= frame <= 100 else 0.0), (0.0, 1.0, 0.0))


def test_player_velocity_is_not_polluted_by_camera_motion():
    # Ein stehender Spieler, Kamera schwenkt 50 Bilder und stoppt. Danach fehlt die Erkennung
    # 20 Bilder lang: Wäre die Kamerabewegung in die Spielergeschwindigkeit geflossen (~4 px/Bild),
    # läge die Vorhersage nach der Lücke ~80 px daneben und die ID risse.
    frames = []
    for frame in range(0, FRAME_COUNT, EVERY):
        if 105 <= frame < 125:
            frames.append(FrameDetections(frame, ()))
            continue
        box = Detection(500.0 + _slow_pan_offset(frame), 500.0, BOX_W, BOX_H, 0.9)
        frames.append(FrameDetections(frame, (box,)))

    tracks = _track(frames, _path(_slow_pan_matrix))

    assert len(tracks) == 1
    assert tracks[0].points[-1].frame >= FRAME_COUNT - 10


# --- Rückfall bei unbekannter Kamera ---


def test_tracker_falls_back_to_unshifted_prediction_when_camera_unknown():
    people = [Walker(100, 300), Walker(600, 500, vx=-1.0), Walker(1000, 700, vx=0.5)]
    frames = make_frames(people, 400, shift_from=200, shift=5.0)  # kleiner Ruck, IoU bleibt hoch
    unknown = _path(lambda f: None, frame_count=400)

    with_unknown_camera = _track(frames, unknown, frame_count=400)
    without_camera = _track(frames, None, frame_count=400)

    assert len(with_unknown_camera) == 3
    assert with_unknown_camera == without_camera


# --- Rückwärtsverträglichkeit ---


def test_tracking_without_camera_gives_same_tracks_as_before():
    a = Walker(x0=100, y0=500, vx=1.0)
    b = Walker(x0=300, y0=510, vx=-1.0)
    # Lücke 95 -> 125 = 30 Bilder (1,2 s) < track_max_lost_seconds (1,5 s): wird überbrückt.
    c = Walker(x0=900, y0=700, missing=((100, 125),))
    frames = make_frames([a, b, c], 300)

    default = _track(frames, None, frame_count=300)
    explicit = _track(frames, NO_CAMERA, frame_count=300)

    assert default == explicit
    assert len(default) == 3
