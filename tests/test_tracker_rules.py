"""T4: Verhaltensregeln des ByteTrackLikeTracker (künstliche Daten, keine Videos).

Annahmen der Testdaten: 25 fps, Bild 1920x1080, Erkennung auf jedem 5. Bild, Boxen 20x50 px,
Bewegung 1 px pro Bild (5 px pro Erkennungsschritt, Überlappung benachbarter Schritte ~0,6).
"""

from dataclasses import dataclass

from matchstats.application.tracker import ByteTrackLikeTracker
from matchstats.domain.detection import Detection
from matchstats.domain.settings import Settings
from matchstats.domain.tracking import FrameDetections

FPS = 25.0
FRAME_SIZE = (1920, 1080)
EVERY = 5
BOX_W, BOX_H = 20.0, 50.0


@dataclass(frozen=True)
class Walker:
    """Person mit konstanter Geschwindigkeit, sichtbar in [first, last] (Bildindizes)."""

    x0: float
    y0: float
    vx: float = 1.0
    vy: float = 0.0
    first: int = 0
    last: int = 10_000
    score: float = 0.9
    # Bildbereiche [von, bis), in denen nichts erkannt wird
    missing: tuple[tuple[int, int], ...] = ()

    def box_at(self, frame: int) -> tuple[float, float]:
        return self.x0 + self.vx * frame, self.y0 + self.vy * frame

    def seen_at(self, frame: int) -> bool:
        if not self.first <= frame <= self.last:
            return False
        return not any(a <= frame < b for a, b in self.missing)


def make_frames(
    walkers: list[Walker], frame_count: int, shift_from: int | None = None, shift: float = 0.0
) -> list[FrameDetections]:
    """Ein FrameDetections je Erkennungsschritt (auch leere). Optional: ab shift_from alle Boxen
    um `shift` px in x verschoben (gemeinsame Verschiebung, z. B. Kamerawackler)."""
    frames = []
    for frame in range(0, frame_count, EVERY):
        dets = []
        for walker in walkers:
            if walker.seen_at(frame):
                x, y = walker.box_at(frame)
                if shift_from is not None and frame >= shift_from:
                    x += shift
                dets.append(Detection(x, y, BOX_W, BOX_H, walker.score))
        frames.append(FrameDetections(frame=frame, detections=tuple(dets)))
    return frames


def run(walkers, frame_count, settings=None, **kwargs):
    settings = settings or Settings()
    tracker = ByteTrackLikeTracker(settings, FPS)
    return tracker.track(make_frames(walkers, frame_count, **kwargs), frame_count, FRAME_SIZE)


def _gap_seconds_to_frames(seconds: float) -> int:
    return int(seconds * FPS)


# --- Regel 1 bis 3: Identität über Zeit und Lücken ---


def test_tracker_keeps_one_id_for_a_steadily_moving_person_over_60_seconds():
    frame_count = int(60 * FPS)

    tracks = run([Walker(100, 500)], frame_count)

    assert len(tracks) == 1
    assert tracks[0].points[0].frame == 0
    assert tracks[0].points[-1].frame >= frame_count - EVERY


def test_tracker_keeps_id_when_detection_is_missing_briefly():
    # 1 s ohne Erkennung < track_max_lost_seconds (1,5 s)
    gap = (200, 200 + _gap_seconds_to_frames(1.0))

    tracks = run([Walker(100, 500, missing=(gap,))], 600)

    assert len(tracks) == 1


def test_tracker_marks_bridged_frames_of_a_short_gap_as_not_visible():
    gap = (200, 225)

    (track,) = run([Walker(100, 500, missing=(gap,))], 600)

    by_frame = {p.frame: p for p in track.points}
    assert by_frame[205].visible is False
    assert by_frame[220].visible is False
    assert by_frame[195].visible is True
    assert by_frame[225].visible is True


def test_tracker_ends_track_and_gives_new_id_when_gap_exceeds_max_lost_seconds():
    gap = (200, 200 + _gap_seconds_to_frames(3.0))  # 3 s > 1,5 s

    tracks = run([Walker(100, 500, missing=(gap,))], 600)

    assert len(tracks) == 2
    first, second = sorted(tracks, key=lambda t: t.points[0].frame)
    assert first.id != second.id
    assert first.points[-1].frame < gap[0]
    assert second.points[0].frame >= gap[1]


def test_tracker_does_not_bridge_gap_just_over_the_limit_but_bridges_just_under():
    settings = Settings(track_max_lost_seconds=1.0)
    under = (200, 215)  # letzter Treffer Bild 195, nächster 215: 0,8 s Abstand
    over = (200, 250)  # letzter Treffer Bild 195, nächster 250: 2,2 s Abstand

    assert len(run([Walker(100, 500, missing=(under,))], 600, settings)) == 1
    assert len(run([Walker(100, 500, missing=(over,))], 600, settings)) == 2


# --- Regel 4: Kreuzung ---


def test_tracker_keeps_ids_when_two_people_cross_paths():
    # A läuft nach rechts, B nach links, beide kreuzen sich bei Bild 100 (kleiner y-Versatz).
    a = Walker(x0=100, y0=500, vx=1.0)
    b = Walker(x0=300, y0=510, vx=-1.0)

    tracks = run([a, b], 200)

    assert len(tracks) == 2
    for track in tracks:
        xs = [p.x for p in track.points]
        # Eine Spur bewegt sich durchgehend in eine Richtung: kein Seitenwechsel der ID
        steps = [later - earlier for earlier, later in zip(xs, xs[1:], strict=False)]
        assert all(s > 0 for s in steps) or all(s < 0 for s in steps)


# --- Regel 5: niedrige Scores ---


def test_low_score_detection_extends_a_track_but_does_not_open_one():
    settings = Settings()
    low = (settings.detect_min_score + settings.track_high_score) / 2  # zwischen den Schwellen

    # Nur niedrige Scores: keine Spur
    assert run([Walker(100, 800, score=low)], 400) == []

    # Hoher Score eröffnet (bis Bild 100), niedriger verlängert (ab Bild 105): eine Spur
    (track,) = run([Walker(100, 500, last=100), Walker(100, 500, first=105, score=low)], 400)
    seen_low = [p for p in track.points if p.visible and p.frame >= 105]
    assert seen_low and all(p.score == low for p in seen_low)


def test_score_below_detect_min_score_is_ignored_by_the_tracker():
    settings = Settings()
    too_low = settings.detect_min_score / 2

    assert run([Walker(100, 500, score=too_low)], 200, settings) == []


# --- Regel 6: Mindesttreffer ---


def test_single_false_detection_does_not_create_a_track():
    blip = Walker(500, 300, first=100, last=100)

    assert run([blip], 300) == []


def test_track_is_confirmed_once_it_has_track_min_hits_hits():
    settings = Settings()
    hits = settings.track_min_hits
    last = (hits - 1) * EVERY
    walker = Walker(500, 300, first=100, last=100 + last)

    tracks = run([walker], 300, settings)

    assert len(tracks) == 1
    assert sum(p.visible for p in tracks[0].points) == hits


def test_track_with_one_hit_less_than_track_min_hits_is_not_output():
    settings = Settings(track_min_hits=3)
    walker = Walker(500, 300, first=100, last=105)  # nur 2 Treffer

    assert run([walker], 300, settings) == []


# --- Regel 7: gemeinsame Verschiebung ---


def test_small_common_shift_of_all_boxes_does_not_change_ids():
    people = [Walker(100, 300), Walker(600, 500, vx=-1.0), Walker(1000, 700, vx=0.5)]

    plain = run(people, 400)
    shifted = run(people, 400, shift_from=200, shift=5.0)

    assert len(plain) == 3
    assert len(shifted) == 3
    assert sorted(t.id for t in shifted) == sorted(t.id for t in plain)
    assert all(t.points[0].frame == 0 and t.points[-1].frame >= 395 for t in shifted)


# --- Regel 9: Bildrand ---


def test_track_vanishing_at_image_edge_ends_and_newcomer_there_gets_new_id():
    margin = Settings().track_edge_margin_px
    # läuft nach rechts aus dem Bild: letztes Treffer-Bild 175, Box endet bei x = 1895 > 1920 - 40
    leaver = Walker(x0=1700, y0=500, vx=1.0, last=175)
    assert 1700 + 175 + BOX_W > FRAME_SIZE[0] - margin
    # Neuer am gleichen Ort kurz danach (deutlich unter 1,5 s Wartezeit)
    newcomer = Walker(x0=1890, y0=500, vx=0.0, first=190, last=210)

    tracks = run([leaver, newcomer], 300)

    assert len(tracks) == 2
    assert len({t.id for t in tracks}) == 2


def test_track_vanishing_away_from_edge_is_continued_by_a_detection_at_same_place():
    # Gegenprobe: gleiche Lücke mitten im Bild wird überbrückt (eine Spur)
    walker = Walker(x0=900, y0=500, vx=1.0, missing=((180, 190),))

    assert len(run([walker], 300)) == 1


# --- Regel 10: IDs ---


def test_ids_are_never_reused_and_increase_in_order_of_appearance():
    walkers = [
        Walker(100, 300, first=0, last=100),
        Walker(300, 600, first=300, last=400),
        Walker(500, 800, first=600, last=700),
    ]

    tracks = sorted(run(walkers, 800), key=lambda t: t.points[0].frame)

    ids = [t.id for t in tracks]
    assert len(ids) == 3
    assert len(set(ids)) == 3
    assert ids == sorted(ids)


# --- Regel 11: Determinismus ---


def test_same_input_gives_same_output():
    people = [Walker(100, 300), Walker(600, 500, vx=-1.0), Walker(900, 700, missing=((200, 260),))]

    assert run(people, 500) == run(people, 500)


# --- Ausgaberegeln ---


def test_track_points_run_from_first_to_last_hit_without_gaps():
    walker = Walker(100, 500, first=50, last=250)

    (track,) = run([walker], 600)

    frames = [p.frame for p in track.points]
    assert frames[0] == 50
    assert frames[-1] == 250
    assert frames == list(range(50, 251))


def test_hit_frames_carry_box_and_score_of_the_detection_and_are_visible():
    walker = Walker(100, 500, score=0.8, last=100)

    (track,) = run([walker], 300)

    for point in track.points:
        if point.frame % EVERY == 0:
            x, y = walker.box_at(point.frame)
            assert point.visible is True
            assert (point.x, point.y, point.w, point.h) == (x, y, BOX_W, BOX_H)
            assert point.score == 0.8


def test_frames_between_hits_are_linearly_interpolated_and_not_visible_without_score():
    walker = Walker(100, 500, vx=1.0, vy=0.5, last=100)

    (track,) = run([walker], 300)

    between = [p for p in track.points if p.frame % EVERY != 0]
    assert between
    for point in between:
        x, y = walker.box_at(point.frame)
        assert point.visible is False
        assert point.score is None
        assert abs(point.x - x) < 1e-6
        assert abs(point.y - y) < 1e-6
        assert abs(point.w - BOX_W) < 1e-6 and abs(point.h - BOX_H) < 1e-6


def test_uncertainty_is_always_none_in_t4():
    (track,) = run([Walker(100, 500, missing=((200, 225),))], 400)

    assert all(p.uncertainty is None for p in track.points)


def test_unconfirmed_track_candidates_are_not_part_of_the_output():
    tracks = run([Walker(100, 500), Walker(800, 300, first=100, last=100)], 300)

    assert len(tracks) == 1


def test_tracker_returns_no_tracks_for_frames_without_detections():
    assert run([], 100) == []


def test_single_high_hit_followed_by_only_a_low_hit_does_not_become_a_track():
    settings = Settings()
    low = (settings.detect_min_score + settings.track_high_score) / 2
    strong = Walker(100, 500, first=0, last=0)  # nur im ersten Erkennungsbild, hoher Score
    weak = Walker(105, 500, first=5, last=5, score=low)  # danach nur niedrig, gleiche Stelle

    assert run([strong, weak], 100) == []
