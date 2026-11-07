import numpy as np
import pytest

from revive.sources.base import SourceKind
from revive.sources.simulator import EMGSimulator, Scenario


def rms(x: np.ndarray) -> float:
    return float(np.sqrt(np.mean(x**2)))


def test_same_seed_is_repeatable():
    a = EMGSimulator(seed=7, scenario=Scenario.MODERATE)
    b = EMGSimulator(seed=7, scenario=Scenario.MODERATE)
    for _ in range(5):
        np.testing.assert_array_equal(a.generate(123).values, b.generate(123).values)


def test_different_seeds_differ():
    a = EMGSimulator(seed=1).generate(500).values
    b = EMGSimulator(seed=2).generate(500).values
    assert not np.allclose(a, b)


def test_reset_restarts_stream():
    sim = EMGSimulator(seed=3, scenario=Scenario.NOISY)
    first = sim.generate(1000)
    sim.reset()
    again = sim.generate(1000)
    np.testing.assert_array_equal(first.values, again.values)
    np.testing.assert_array_equal(first.timestamps, again.timestamps)


def test_timestamps_follow_sample_rate():
    sim = EMGSimulator(sample_rate=500)
    batch1 = sim.generate(10)
    batch2 = sim.generate(10)
    assert batch1.timestamps[0] == 0.0
    np.testing.assert_allclose(np.diff(np.concatenate([batch1.timestamps, batch2.timestamps])), 1 / 500)


def test_scenarios_order_by_activity():
    def scenario_rms(scenario: Scenario) -> float:
        return rms(EMGSimulator(scenario=scenario).generate(500 * 10).values)

    rest, weak, moderate = (scenario_rms(s) for s in (Scenario.REST, Scenario.WEAK, Scenario.MODERATE))
    assert rest < 0.02
    assert rest < weak < moderate


def test_signal_is_burst_like_not_a_sine():
    values = EMGSimulator(scenario=Scenario.MODERATE).generate(500 * 5).values
    spectrum = np.abs(np.fft.rfft(values))
    # A pure tone concentrates its energy in one bin; EMG-like noise spreads it out.
    assert spectrum.max() / spectrum.sum() < 0.05


def test_noisy_scenario_contains_artifact_spikes():
    values = EMGSimulator(scenario=Scenario.NOISY).generate(500 * 20).values
    assert np.abs(values).max() > 0.5


def test_manual_effort_increases_activity_and_is_clamped():
    sim = EMGSimulator()
    quiet = rms(sim.generate(1000).values)
    sim.manual_effort = 5.0
    assert sim.manual_effort == 1.0
    sim.generate(200)  # let the effort ramp settle
    assert rms(sim.generate(1000).values) > 20 * quiet


def test_read_is_empty_until_started():
    sim = EMGSimulator()
    assert len(sim.read()) == 0
    assert sim.kind is SourceKind.SIMULATION and sim.is_simulated
    sim.start()
    assert sim.is_running
    sim.stop()
    assert len(sim.read()) == 0


@pytest.mark.parametrize("scenario", list(Scenario))
def test_scenarios_have_labels(scenario):
    assert scenario.label
