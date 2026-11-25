"""T5b1: Abstimmung je Spur, Stichprobenwahl, Spur-Fingerabdruck, Kennzahlen (rein, ohne Video)."""

from dataclasses import replace

import pytest

from matchstats.domain.teams import (
    UNKNOWN,
    TeamPrediction,
    TrackTeam,
    class_change_share,
    null_track_count,
    select_sample_points,
    tracks_fingerprint,
    vote_track,
)
from matchstats.domain.testset import CLASSES
from matchstats.domain.tracking import Track, TrackPoint


def preds(*labels):
    return [TeamPrediction(label, None if label is None else 0.9) for label in labels]


def point(frame, visible=True, x=10.0, y=20.0, w=30.0, h=60.0, score=0.9):
    return TrackPoint(frame, x, y, w, h, visible, score if visible else None)


def track(track_id, n=5, **kwargs):
    return Track(track_id, tuple(point(i * 5, **kwargs) for i in range(n)))


def team(track_id=1, label="team_a", votes=None):
    full = {c: 0 for c in (*CLASSES, UNKNOWN)}
    full.update(votes or {})
    return TrackTeam(track_id, label, None, sum(full.values()), full)


# --- vote_track ---------------------------------------------------------------------------


def test_majority_class_wins_the_track():
    result = vote_track(7, preds("team_a", "team_a", "team_b", "team_a"), min_votes=3)

    assert result.id == 7
    assert result.label == "team_a"
    assert result.samples == 4


def test_single_wrong_vote_does_not_flip_the_track():
    result = vote_track(1, preds("team_b", "team_b", "team_b", "team_b", "team_a"), min_votes=3)

    assert result.label == "team_b"


def test_votes_always_contain_all_five_keys_with_zeros():
    result = vote_track(1, preds("team_a", "team_a", "team_a"), min_votes=3)

    assert result.votes == {
        "team_a": 3,
        "team_b": 0,
        "goalkeeper": 0,
        "referee": 0,
        UNKNOWN: 0,
    }


def test_none_prediction_counts_as_unknown_vote_but_does_not_vote_for_a_class():
    result = vote_track(1, preds("team_a", None, "team_a", None, "team_a"), min_votes=3)

    assert result.votes[UNKNOWN] == 2
    assert result.samples == 5
    assert result.label == "team_a"
    assert result.uncertainty == 0.0  # Nenner = nur bekannte Stimmen


def test_label_is_none_when_fewer_known_votes_than_min_votes():
    result = vote_track(1, preds("team_a", "team_a", None, None, None), min_votes=3)

    assert result.label is None


def test_exactly_min_votes_known_is_enough():
    result = vote_track(1, preds("team_a", "team_a", "team_b"), min_votes=3)

    assert result.label == "team_a"


def test_uncertainty_is_quarter_at_three_to_one():
    result = vote_track(1, preds("team_a", "team_a", "team_a", "team_b"), min_votes=3)

    assert result.uncertainty == pytest.approx(0.25)


def test_uncertainty_is_zero_at_four_to_zero():
    result = vote_track(1, preds("team_b", "team_b", "team_b", "team_b"), min_votes=3)

    assert result.uncertainty == 0.0


def test_uncertainty_is_none_without_known_votes():
    result = vote_track(1, preds(None, None, None), min_votes=1)

    assert result.label is None
    assert result.uncertainty is None


def test_uncertainty_is_still_computed_when_label_is_none_for_too_few_votes():
    result = vote_track(1, preds("team_a", "team_b", None, None), min_votes=3)

    assert result.label is None
    assert result.uncertainty == pytest.approx(0.5)


def test_tie_goes_to_class_earlier_in_classes_team_a_first():
    assert vote_track(1, preds("team_b", "team_a", "team_b", "team_a"), 3).label == "team_a"
    assert vote_track(1, preds("referee", "team_b", "team_b", "referee"), 3).label == "team_b"
    assert vote_track(1, preds("referee", "goalkeeper", "referee", "goalkeeper"), 3).label == (
        "goalkeeper"
    )


def test_tie_result_does_not_depend_on_prediction_order():
    a = vote_track(1, preds("team_a", "team_b", "team_a", "team_b"), 3)
    b = vote_track(1, preds("team_b", "team_b", "team_a", "team_a"), 3)

    assert a == b


def test_empty_predictions_give_zero_samples_and_null_label():
    result = vote_track(3, [], min_votes=3)

    assert result.samples == 0
    assert result.label is None
    assert result.uncertainty is None
    assert all(v == 0 for v in result.votes.values())
    assert set(result.votes) == {*CLASSES, UNKNOWN}


# --- select_sample_points -----------------------------------------------------------------


def test_sample_points_are_spread_evenly_over_the_track():
    t = Track(1, tuple(point(i) for i in range(10)))

    chosen = select_sample_points(t, 4)

    assert [p.frame for p in chosen] == [0, 3, 6, 9]  # round(i * 9 / 3)


def test_sample_points_include_first_and_last_visible_point():
    t = Track(1, tuple(point(i) for i in range(21)))

    chosen = select_sample_points(t, 5)

    assert [p.frame for p in chosen] == [0, 5, 10, 15, 20]


def test_sample_points_take_only_visible_points():
    points = tuple(point(i, visible=(i % 2 == 0)) for i in range(10))  # sichtbar: 0,2,4,6,8

    chosen = select_sample_points(Track(1, points), 3)

    assert [p.frame for p in chosen] == [0, 4, 8]
    assert all(p.visible for p in chosen)


def test_sample_points_with_count_one_take_the_middle():
    t = Track(1, tuple(point(i) for i in range(5)))

    assert [p.frame for p in select_sample_points(t, 1)] == [2]


def test_sample_points_return_all_when_track_has_fewer_points_than_count():
    t = Track(1, tuple(point(i) for i in range(3)))

    chosen = select_sample_points(t, 8)

    assert [p.frame for p in chosen] == [0, 1, 2]


def test_sample_points_return_all_when_count_equals_number_of_points():
    t = Track(1, tuple(point(i) for i in range(4)))

    assert [p.frame for p in select_sample_points(t, 4)] == [0, 1, 2, 3]


def test_sample_points_of_empty_track_are_empty():
    assert select_sample_points(Track(1, ()), 8) == ()


def test_sample_points_of_track_without_visible_points_are_empty():
    t = Track(1, tuple(point(i, visible=False) for i in range(5)))

    assert select_sample_points(t, 3) == ()


def test_sample_points_have_no_duplicates_and_are_deterministic():
    t = Track(1, tuple(point(i) for i in range(50)))

    first = select_sample_points(t, 8)
    second = select_sample_points(t, 8)

    assert first == second
    assert len({p.frame for p in first}) == len(first) == 8
    assert [p.frame for p in first] == sorted(p.frame for p in first)


# --- tracks_fingerprint -------------------------------------------------------------------


def test_fingerprint_is_stable_and_a_sha256_hex_string():
    tracks = (track(1), track(2))

    assert tracks_fingerprint(tracks) == tracks_fingerprint(tracks)
    assert len(tracks_fingerprint(tracks)) == 64
    int(tracks_fingerprint(tracks), 16)


def test_fingerprint_changes_when_a_box_changes():
    base = (track(1),)
    moved = (Track(1, (replace(base[0].points[0], x=11.0), *base[0].points[1:])),)

    assert tracks_fingerprint(base) != tracks_fingerprint(moved)


def test_fingerprint_changes_when_visible_flag_changes():
    base = (track(1),)
    changed = (Track(1, (*base[0].points[:2], replace(base[0].points[2], visible=False),
                         *base[0].points[3:])),)  # fmt: skip

    assert tracks_fingerprint(base) != tracks_fingerprint(changed)


def test_fingerprint_changes_when_track_id_or_frame_changes():
    assert tracks_fingerprint((track(1),)) != tracks_fingerprint((track(2),))
    shifted = Track(1, tuple(replace(p, frame=p.frame + 1) for p in track(1).points))
    assert tracks_fingerprint((track(1),)) != tracks_fingerprint((shifted,))


def test_fingerprint_ignores_score_and_uncertainty():
    base = (track(1),)
    other = (Track(1, tuple(replace(p, score=0.1, uncertainty=0.7) for p in base[0].points)),)

    assert tracks_fingerprint(base) == tracks_fingerprint(other)


def test_fingerprint_does_not_depend_on_track_order():
    assert tracks_fingerprint((track(1), track(2, w=40.0))) == tracks_fingerprint(
        (track(2, w=40.0), track(1))
    )


def test_fingerprint_ignores_differences_below_two_decimals():
    base = (track(1),)
    tiny = (Track(1, tuple(replace(p, x=p.x + 0.001) for p in base[0].points)),)

    assert tracks_fingerprint(base) == tracks_fingerprint(tiny)


def test_fingerprint_of_no_tracks_is_defined():
    assert len(tracks_fingerprint(())) == 64


# --- class_change_share / null_track_count ------------------------------------------------


def test_class_change_share_counts_tracks_with_a_vote_for_another_known_class():
    teams = [
        team(1, "team_a", {"team_a": 4}),
        team(2, "team_a", {"team_a": 3, "team_b": 1}),
        team(3, "team_b", {"team_b": 3, "referee": 1}),
        team(4, "team_b", {"team_b": 4}),
    ]

    assert class_change_share(teams) == pytest.approx(0.5)


def test_class_change_share_ignores_unknown_votes():
    teams = [team(1, "team_a", {"team_a": 3, UNKNOWN: 5})]

    assert class_change_share(teams) == 0.0


def test_class_change_share_denominator_excludes_null_tracks():
    teams = [
        team(1, "team_a", {"team_a": 3, "team_b": 1}),
        team(2, None, {"team_a": 1, "team_b": 1}),
        team(3, None, {UNKNOWN: 3}),
    ]

    assert class_change_share(teams) == 1.0


def test_class_change_share_is_none_without_labelled_tracks():
    assert class_change_share([]) is None
    assert class_change_share([team(1, None, {UNKNOWN: 2})]) is None


def test_null_track_count_counts_tracks_without_label():
    teams = [team(1, "team_a", {"team_a": 3}), team(2, None), team(3, None)]

    assert null_track_count(teams) == 2
    assert null_track_count([]) == 0


# --- select_sample_points mit Mindesthöhe (T5c1) ---------------------------------------


def test_sample_points_with_min_height_only_use_points_at_or_above_it():
    t = Track(1, tuple(point(i, h=h) for i, h in enumerate([10.0, 47.9, 48.0, 90.0])))

    chosen = select_sample_points(t, 8, min_height=48.0)

    assert [p.frame for p in chosen] == [2, 3]  # 48.0 liegt genau auf der Grenze


def test_sample_points_are_drawn_from_the_tall_points_only():
    t = Track(1, tuple(point(i, h=10.0 if i < 10 else 80.0) for i in range(20)))

    chosen = select_sample_points(t, 4, min_height=48.0)

    assert [p.frame for p in chosen] == [10, 13, 16, 19]


def test_sample_points_without_min_height_argument_ignore_height():
    t = Track(1, tuple(point(i, h=1.0) for i in range(3)))

    assert [p.frame for p in select_sample_points(t, 8)] == [0, 1, 2]


def test_sample_points_all_below_min_height_give_empty_tuple():
    t = Track(1, tuple(point(i, h=5.0) for i in range(5)))

    assert select_sample_points(t, 3, min_height=48.0) == ()
