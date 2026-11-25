"""T5a: Farbverfahren für die Teamzuordnung, nur mit künstlichen Bildern (kein Video).

Vertrag: classify(images, boxes) bekommt gleich viele Bilder wie Boxen; Box i liegt in Bild i
(dasselbe Bild darf mehrfach übergeben werden). Die Rückgabe hat dieselbe Länge und Reihenfolge.
"""

import numpy as np

from matchstats.application.team_classifier import TeamClassifier
from matchstats.domain.detection import Detection
from matchstats.domain.settings import Settings
from matchstats.domain.teams import TeamPrediction
from matchstats.infrastructure.color_team_classifier import ColorTeamClassifier

GRASS = (60, 160, 60)
RED = (200, 30, 30)
BLUE = (30, 40, 200)
YELLOW = (230, 220, 20)
SHORTS = (20, 20, 20)
BLACK = (15, 15, 15)
GRAY = (128, 128, 128)
BOX_W, BOX_H = 40, 100


def make_settings(**overrides) -> Settings:
    values = dict(
        team_upper_body_fraction=0.5,
        team_min_box_height_px=20,
        team_min_box_width_px=8,
        team_grass_hue_range=(35, 85),
        team_grass_min_saturation=40,
        team_cluster_count=3,
        team_outlier_max_share=0.2,
        team_min_pixels=30,
    )
    values.update(overrides)
    return Settings(**values)


def make_scene(colors, grass_margin=0, seed=0, per_row=6):
    """Rasenbild mit einem Spieler je Farbe (Oberkörper Trikot, unten dunkel), leichtes Rauschen."""
    rng = np.random.default_rng(seed)
    rows = (len(colors) + per_row - 1) // per_row
    image = np.zeros((rows * (BOX_H + 20) + 20, per_row * (BOX_W + 20) + 20, 3), np.uint8)
    image[:] = GRASS
    boxes = []
    for i, color in enumerate(colors):
        x = 10 + (i % per_row) * (BOX_W + 20)
        y = 10 + (i // per_row) * (BOX_H + 20)
        patch = np.empty((BOX_H, BOX_W, 3), np.uint8)
        patch[: BOX_H // 2] = color
        patch[BOX_H // 2 :] = SHORTS
        if grass_margin:
            patch[:, :grass_margin] = GRASS
            patch[:, BOX_W - grass_margin :] = GRASS
        noise = rng.integers(-3, 4, patch.shape)
        image[y : y + BOX_H, x : x + BOX_W] = np.clip(patch.astype(int) + noise, 0, 255)
        boxes.append(Detection(x, y, BOX_W, BOX_H, 1.0))
    return image, boxes


def classify(image, boxes, **overrides):
    return ColorTeamClassifier(make_settings(**overrides)).classify([image] * len(boxes), boxes)


def labels(predictions):
    return [p.label for p in predictions]


TWO_TEAMS = [RED] * 6 + [BLUE] * 6


def test_new_settings_fields_exist_with_sensible_defaults():
    s = Settings()

    assert 0 < s.team_upper_body_fraction <= 1
    assert s.team_min_box_height_px > 0 and s.team_min_box_width_px > 0
    low, high = s.team_grass_hue_range
    assert 0 <= low < high <= 179
    assert 0 <= s.team_grass_min_saturation <= 255
    assert s.team_cluster_count >= 4  # zwei Teams plus Torwart und Schiedsrichter
    assert 0 < s.team_outlier_max_share < 0.5
    assert s.team_min_pixels > 0


def test_color_classifier_fulfils_the_team_classifier_port():
    classifier: TeamClassifier = ColorTeamClassifier(make_settings())
    image, boxes = make_scene([RED])

    result = classifier.classify([image], boxes)

    assert isinstance(result, list) and isinstance(result[0], TeamPrediction)


def test_classify_returns_one_prediction_per_box_in_same_order():
    image, boxes = make_scene(TWO_TEAMS)

    result = labels(classify(image, boxes))

    assert len(result) == len(boxes)
    assert result[:6] == [result[0]] * 6
    assert result[6:] == [result[6]] * 6


def test_two_jersey_colors_are_separated_into_two_teams():
    image, boxes = make_scene(TWO_TEAMS)

    result = labels(classify(image, boxes))

    assert result[0] != result[6]
    assert {result[0], result[6]} == {"team_a", "team_b"}


def test_confidence_is_between_zero_and_one_for_known_boxes():
    image, boxes = make_scene(TWO_TEAMS)

    for p in classify(image, boxes):
        assert p.confidence is not None and 0.0 <= p.confidence <= 1.0


def test_third_small_color_group_becomes_outlier_class():
    image, boxes = make_scene(TWO_TEAMS + [YELLOW])

    result = labels(classify(image, boxes))

    assert result[-1] in ("goalkeeper", "referee")
    assert {result[0], result[6]} == {"team_a", "team_b"}


def test_grass_in_box_margin_does_not_change_result():
    clean_image, boxes = make_scene(TWO_TEAMS + [YELLOW])
    grassy_image, _ = make_scene(TWO_TEAMS + [YELLOW], grass_margin=10)

    assert labels(classify(grassy_image, boxes)) == labels(classify(clean_image, boxes))


def test_empty_box_gives_unknown():
    image, boxes = make_scene(TWO_TEAMS)
    boxes.append(Detection(5, 5, 0, 0, 1.0))

    result = classify(image, boxes)

    assert result[-1].label is None and result[-1].confidence is None
    assert all(p.label is not None for p in result[:-1])


def test_tiny_box_gives_unknown_not_random_class():
    image, boxes = make_scene(TWO_TEAMS)
    boxes.append(Detection(10, 10, 4, 10, 1.0))  # unter Mindestbreite und -höhe

    assert classify(image, boxes)[-1].label is None


def test_box_below_min_height_only_gives_unknown():
    image, boxes = make_scene(TWO_TEAMS)
    boxes.append(Detection(10, 10, BOX_W, 15, 1.0))  # Höhe < 20

    assert classify(image, boxes)[-1].label is None


def test_box_below_min_width_only_gives_unknown():
    image, boxes = make_scene(TWO_TEAMS)
    boxes.append(Detection(10, 10, 6, BOX_H, 1.0))  # Breite < 8

    assert classify(image, boxes)[-1].label is None


def test_box_outside_image_gives_unknown():
    image, boxes = make_scene(TWO_TEAMS)
    boxes.append(Detection(image.shape[1] + 50, image.shape[0] + 50, BOX_W, BOX_H, 1.0))

    assert classify(image, boxes)[-1].label is None


def test_box_partly_outside_image_does_not_crash():
    image, boxes = make_scene(TWO_TEAMS)
    boxes.append(Detection(image.shape[1] - 10, image.shape[0] - 30, BOX_W, BOX_H, 1.0))

    assert len(classify(image, boxes)) == len(boxes)


def test_pure_grass_box_gives_unknown():
    image, boxes = make_scene(TWO_TEAMS)
    pad = np.full((BOX_H + 20, image.shape[1], 3), GRASS, np.uint8)
    image = np.vstack([image, pad])
    boxes.append(Detection(10, image.shape[0] - BOX_H - 10, BOX_W, BOX_H, 1.0))

    assert classify(image, boxes)[-1].label is None


def test_too_few_non_grass_pixels_gives_unknown():
    # Nur ein 2 Pixel breiter Trikotstreifen im Oberkörper, Rest Rasen: unter team_min_pixels.
    image = np.full((200, 200, 3), GRASS, np.uint8)
    image[20:70, 30:32] = RED
    boxes = [Detection(10, 20, BOX_W, BOX_H, 1.0)]

    assert classify(image, boxes, team_min_pixels=500)[0].label is None


def test_single_jersey_color_does_not_invent_second_team():
    image, boxes = make_scene([RED] * 8)

    result = labels(classify(image, boxes))

    assert len(set(result)) == 1
    assert result[0] in ("team_a", "team_b")


def test_result_is_deterministic():
    image, boxes = make_scene(TWO_TEAMS + [YELLOW])

    first = classify(image, boxes)
    second = classify(image.copy(), list(boxes))

    assert first == second


def test_classify_works_across_several_images_of_one_clip():
    image1, boxes1 = make_scene([RED] * 3 + [BLUE] * 3)
    image2, boxes2 = make_scene([BLUE] * 3 + [RED] * 3, seed=1)

    result = ColorTeamClassifier(make_settings()).classify(
        [image1] * 6 + [image2] * 6, boxes1 + boxes2
    )

    assert len(result) == 12
    assert labels(result)[0] == labels(result)[9]  # beide rot
    assert labels(result)[0] != labels(result)[3]


OUTLIER_LABELS = ("goalkeeper", "referee")


def test_two_outlier_colors_get_two_different_outlier_labels_and_no_team():
    colors = [RED] * 10 + [BLUE] * 10 + [YELLOW] + [BLACK] * 2
    image, boxes = make_scene(colors)

    result = labels(classify(image, boxes, team_cluster_count=4))

    yellow, black = result[20], set(result[21:])
    assert len(black) == 1
    assert yellow not in ("team_a", "team_b") and yellow is not None
    assert black.isdisjoint({"team_a", "team_b", None})
    assert yellow != next(iter(black))
    assert {yellow, *black} == set(OUTLIER_LABELS)
    assert {result[0], result[10]} == {"team_a", "team_b"}


def test_larger_outlier_group_is_referee_and_smaller_is_goalkeeper():
    colors = [RED] * 10 + [BLUE] * 10 + [YELLOW] + [BLACK] * 2
    image, boxes = make_scene(colors)

    result = labels(classify(image, boxes, team_cluster_count=4))

    assert result[20] == "goalkeeper"
    assert result[21:] == ["referee"] * 2


def test_two_largest_color_groups_are_teams_even_when_one_is_small():
    image, boxes = make_scene([RED] * 20 + [BLUE] * 3)

    result = labels(classify(image, boxes))  # 3 von 23 = 13 %, unter team_outlier_max_share

    assert set(result[:20]) | set(result[20:]) == {"team_a", "team_b"}
    assert result[20:] == [result[20]] * 3
    assert result[20] != result[0]


def test_two_largest_groups_are_teams_even_when_small_with_four_clusters():
    image, boxes = make_scene([RED] * 20 + [BLUE] * 3 + [YELLOW])

    result = labels(classify(image, boxes, team_cluster_count=4))

    assert result[20:23] == ["team_b"] * 3 and result[0] == "team_a"
    assert result[23] in OUTLIER_LABELS


def test_single_noise_box_does_not_pull_real_outliers_into_the_teams():
    image, boxes = make_scene([RED] * 10 + [BLUE] * 10 + [YELLOW] * 2 + [GRAY])

    result = labels(classify(image, boxes, team_cluster_count=3))

    assert result[20] == result[21]  # beide gelben Boxen: dasselbe Label
    assert result[20] not in ("team_a", "team_b")
    assert result[20] is not None
    assert {result[0], result[10]} == {"team_a", "team_b"}


def test_single_noise_box_does_not_pull_real_outliers_into_the_teams_with_four_clusters():
    image, boxes = make_scene([RED] * 10 + [BLUE] * 10 + [YELLOW] * 2 + [GRAY])

    result = labels(classify(image, boxes, team_cluster_count=4))

    assert result[20] == result[21] and result[20] not in ("team_a", "team_b", None)


def test_last_group_sizes_lists_group_sizes_descending():
    image, boxes = make_scene([RED] * 10 + [BLUE] * 6 + [YELLOW] * 2)
    classifier = ColorTeamClassifier(make_settings(team_cluster_count=4))

    classifier.classify([image] * len(boxes), boxes)

    assert classifier.last_group_sizes() == [10, 6, 2]


DARK_RED = (140, 20, 20)  # gleiche Trikotfarbe bei anderem Licht, über team_min_cluster_distance


def test_three_large_color_groups_leave_no_unknown_and_similar_reds_share_one_team():
    image, boxes = make_scene([RED] * 10 + [DARK_RED] * 10 + [BLUE] * 10)

    result = labels(classify(image, boxes, team_cluster_count=4))

    assert None not in result
    assert set(result) == {"team_a", "team_b"}
    assert set(result[:10]) == set(result[10:20]) and len(set(result[:10])) == 1
    assert result[0] != result[20]


def test_large_third_group_is_assigned_to_nearest_team_not_to_outlier_class():
    # 6 von 26 = 23 % und damit über team_outlier_max_share (0,2): kein Ausreißer.
    image, boxes = make_scene([RED] * 10 + [BLUE] * 10 + [YELLOW] * 6)

    result = labels(classify(image, boxes, team_cluster_count=4))

    assert set(result[20:]) <= {"team_a", "team_b"}
    assert len(set(result[20:])) == 1
    assert set(result[20:]) == set(result[:10])  # Gelb liegt näher an Rot als an Blau
    assert result[0] != result[10]


def test_large_third_group_does_not_take_goalkeeper_or_referee_label():
    image, boxes = make_scene([RED] * 10 + [DARK_RED] * 8 + [BLUE] * 10)

    result = labels(classify(image, boxes, team_cluster_count=4))

    assert "goalkeeper" not in result and "referee" not in result and None not in result


def test_single_small_outliers_stay_goalkeeper_and_referee_next_to_large_third_group():
    colors = [RED] * 10 + [DARK_RED] * 10 + [BLUE] * 10 + [YELLOW] + [BLACK] * 2
    image, boxes = make_scene(colors)

    result = labels(classify(image, boxes, team_cluster_count=5))

    assert result[30] in OUTLIER_LABELS
    assert set(result[31:]) <= set(OUTLIER_LABELS)
    assert result[30] != result[31]
    assert set(result[:30]) == {"team_a", "team_b"}


def test_one_and_two_box_outliers_stay_outliers_with_two_teams():
    for count in (1, 2):
        image, boxes = make_scene([RED] * 10 + [BLUE] * 10 + [YELLOW] * count)

        result = labels(classify(image, boxes, team_cluster_count=4))

        assert set(result[20:]) <= set(OUTLIER_LABELS)
