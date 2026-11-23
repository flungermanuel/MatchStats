"""T4b: Kamerabewegung als Datentyp (CameraMotion, CameraPath, Matrixrechnung), ohne Bilder."""

import pytest
from matchstats.domain.camera import (
    IDENTITY,
    NO_CAMERA,
    CameraMotion,
    CameraPath,
    apply_to_box,
    compose,
)


def _shift(dx: float, dy: float):
    return ((1.0, 0.0, dx), (0.0, 1.0, dy))


def _path(*matrices) -> CameraPath:
    """Pfad mit Bildern 1, 2, 3, ...; None = Schätzung fehlgeschlagen."""
    return CameraPath(
        motions=tuple(
            CameraMotion(frame=i, matrix=m, quality=None if m is None else 1.0)
            for i, m in enumerate(matrices, start=1)
        )
    )


def test_camera_path_is_identity_for_same_frame():
    assert _path(_shift(5, 0)).transform(3, 3) == IDENTITY
    assert NO_CAMERA.transform(7, 7) == IDENTITY


def test_camera_path_chains_shifts_over_intermediate_frames():
    path = _path(_shift(1, 0), _shift(2, 0), _shift(0, 3))

    assert path.transform(0, 3) == _shift(3, 3)  # Bilder 1, 2, 3
    assert path.transform(1, 3) == _shift(2, 3)  # nur Bilder 2 und 3
    assert path.transform(0, 1) == _shift(1, 0)


def test_camera_path_moves_box_with_the_chained_transform():
    path = _path(_shift(1, 0), _shift(2, 0), _shift(0, 3))

    assert path.shift_box(10.0, 20.0, 20.0, 50.0, 0, 3) == (13.0, 23.0, 20.0, 50.0)


def test_camera_path_is_unknown_when_any_step_is_unknown():
    path = _path(_shift(1, 0), None, _shift(0, 3))

    assert path.transform(0, 3) is None
    assert path.transform(0, 1) == _shift(1, 0)  # Glieder davor sind bekannt
    assert path.transform(2, 3) == _shift(0, 3)  # und danach


def test_camera_path_is_unknown_when_a_frame_is_missing_in_the_path():
    assert _path(_shift(1, 0)).transform(0, 2) is None


def test_unknown_transform_leaves_box_unchanged_instead_of_assuming_zero_motion():
    path = _path(_shift(1, 0), None)

    assert path.shift_box(10.0, 20.0, 20.0, 50.0, 0, 2) == (10.0, 20.0, 20.0, 50.0)


def test_camera_path_rejects_backward_direction():
    with pytest.raises(ValueError):
        _path(_shift(1, 0), _shift(1, 0)).transform(2, 1)


def test_compose_applies_first_matrix_before_second():
    # erst um 2 skalieren, dann um (10, 0) verschieben: Punkt (1, 1) -> (2, 2) -> (12, 2)
    scale = ((2.0, 0.0, 0.0), (0.0, 2.0, 0.0))

    assert compose(scale, _shift(10, 0)) == ((2.0, 0.0, 10.0), (0.0, 2.0, 0.0))
    # umgekehrte Reihenfolge: (1, 1) -> (11, 1) -> (22, 2)
    assert compose(_shift(10, 0), scale) == ((2.0, 0.0, 20.0), (0.0, 2.0, 0.0))


def test_compose_with_identity_changes_nothing():
    matrix = ((1.1, 0.0, 5.0), (0.0, 1.1, -3.0))

    assert compose(matrix, IDENTITY) == matrix
    assert compose(IDENTITY, matrix) == matrix


def test_apply_to_box_moves_a_box_by_pure_translation():
    assert apply_to_box(_shift(5, -2), 10.0, 20.0, 20.0, 50.0) == (15.0, 18.0, 20.0, 50.0)


def test_apply_to_box_scales_size_with_zoom():
    zoom = ((2.0, 0.0, 0.0), (0.0, 2.0, 0.0))

    # Boxmitte (20, 30) -> (40, 60); Größe 20x40 -> 40x80; linke obere Ecke (20, 20)
    assert apply_to_box(zoom, 10.0, 10.0, 20.0, 40.0) == (20.0, 20.0, 40.0, 80.0)


def test_no_camera_leaves_box_unchanged():
    assert NO_CAMERA.shift_box(10.0, 20.0, 20.0, 50.0, 0, 40) == (10.0, 20.0, 20.0, 50.0)


def test_failed_estimate_is_stored_as_missing_matrix_and_not_as_identity():
    motion = CameraMotion(frame=4, matrix=None, quality=None)

    assert motion.matrix is None
