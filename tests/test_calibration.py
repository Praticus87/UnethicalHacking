import numpy as np
import pytest

from revive.core.calibration import Calibration, estimate_reference_level, estimate_rest_level


def test_normalize_maps_rest_to_zero_and_reference_to_one():
    cal = Calibration(rest_level=0.1, reference_level=0.5)
    np.testing.assert_allclose(cal.normalize(np.array([0.0, 0.1, 0.3, 0.5, 2.0])), [0, 0, 0.5, 1, 1])


def test_invalid_calibration_rejected():
    with pytest.raises(ValueError):
        Calibration(rest_level=0.5, reference_level=0.5)


def test_from_recordings():
    rng = np.random.default_rng(0)
    rest = 0.02 + 0.002 * rng.standard_normal(1000)
    active = 0.6 + 0.05 * rng.standard_normal(1000)
    cal = Calibration.from_recordings(rest, active)
    assert 0.02 < cal.rest_level < 0.025
    assert 0.6 < cal.reference_level < 0.75
    assert np.mean(cal.normalize(rest)) < 0.01


def test_estimates_require_data():
    with pytest.raises(ValueError):
        estimate_rest_level(np.empty(0))
    with pytest.raises(ValueError):
        estimate_reference_level(np.empty(0))
