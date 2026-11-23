"""T4b: OpenCV-Schätzer der Kamerabewegung an künstlichen Bildern (Zufallstextur, fester Seed)."""

import numpy as np
import pytest

from matchstats.domain.settings import Settings

cv2 = pytest.importorskip("cv2")

from matchstats.infrastructure.opencv_camera import OpenCvCameraMotionEstimator  # noqa: E402

WIDTH, HEIGHT = 480, 270


def _texture() -> np.ndarray:
    """Geglättetes Zufallsbild mit vielen Ecken, als RGB (HEIGHT, WIDTH, 3)."""
    rng = np.random.default_rng(42)
    noise = rng.integers(0, 256, size=(HEIGHT, WIDTH), dtype=np.uint8)
    smooth = cv2.GaussianBlur(noise, (0, 0), 2.0)
    smooth = cv2.normalize(smooth, None, 0, 255, cv2.NORM_MINMAX)
    return np.dstack([smooth] * 3)


def _warp(image: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Bild so verzerren, dass ein Punkt p im Ausgangsbild nach matrix @ p wandert."""
    return cv2.warpAffine(
        image, matrix.astype(np.float64), (WIDTH, HEIGHT), borderMode=cv2.BORDER_REFLECT
    )


def _estimate(first, second, **settings):
    estimator = OpenCvCameraMotionEstimator(Settings(**settings))
    return estimator.estimate(iter([(0, first), (1, second)]))


def test_estimator_recovers_known_shift_and_zoom():
    base = _texture()

    shift = np.array([[1.0, 0.0, 6.0], [0.0, 1.0, -4.0]])
    (motion,) = _estimate(base, _warp(base, shift))
    assert motion.frame == 1
    assert motion.matrix is not None
    np.testing.assert_allclose(np.array(motion.matrix), shift, atol=1.0)

    s = 1.05  # Zoom um das Bildzentrum
    zoom = np.array([[s, 0.0, WIDTH / 2 * (1 - s)], [0.0, s, HEIGHT / 2 * (1 - s)]])
    (motion,) = _estimate(base, _warp(base, zoom))
    assert motion.matrix is not None
    estimated = np.array(motion.matrix)
    assert estimated[0, 0] == pytest.approx(s, rel=0.01)
    assert estimated[1, 1] == pytest.approx(s, rel=0.01)
    np.testing.assert_allclose(estimated[:, 2], zoom[:, 2], atol=2.0)


def test_estimator_returns_matrix_in_full_resolution_when_working_at_half_size():
    base = _texture()
    shift = np.array([[1.0, 0.0, 6.0], [0.0, 1.0, -4.0]])

    (motion,) = _estimate(base, _warp(base, shift), camera_downscale=0.5)

    assert motion.matrix is not None
    # Verschiebung ist in Pixeln der vollen Auflösung angegeben (6 und -4, nicht 3 und -2)
    np.testing.assert_allclose(np.array(motion.matrix), shift, atol=1.5)


def test_estimator_gives_one_motion_per_frame_starting_at_index_one():
    base = _texture()
    estimator = OpenCvCameraMotionEstimator(Settings())

    motions = estimator.estimate(iter([(0, base), (1, base), (2, base)]))

    assert [m.frame for m in motions] == [1, 2]


def test_estimator_reports_unknown_motion_for_featureless_image():
    flat = np.full((HEIGHT, WIDTH, 3), 128, dtype=np.uint8)

    (motion,) = _estimate(flat, flat)

    assert motion.matrix is None  # fehlend, nicht Einheitsmatrix
