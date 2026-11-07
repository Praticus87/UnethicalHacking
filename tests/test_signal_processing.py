import numpy as np
import pytest

from revive.core.calibration import Calibration
from revive.core.signal_processing import ContractionDetector, DetectorConfig, EMGProcessor
from revive.sources.simulator import EMGSimulator, Scenario

FS = 500.0


def run_pipeline(sim: EMGSimulator, seconds: float, chunk: int = 50):
    processor = EMGProcessor(sim.sample_rate)
    detector = ContractionDetector()
    calibration = Calibration()
    events = []
    for _ in range(int(seconds * sim.sample_rate / chunk)):
        batch = sim.generate(chunk)
        _, envelope = processor.process(batch.values)
        events += detector.update(batch.timestamps, calibration.normalize(envelope))
    return events, detector


def square_pulse(segments: list[tuple[float, float]]):
    """Build an activation trace from (duration_s, level) segments."""
    values = np.concatenate([np.full(int(d * FS), level) for d, level in segments])
    return np.arange(values.size) / FS, values


# --------------------------------------------------------------- RMS envelope
def test_rms_of_sine_matches_theory():
    t = np.arange(int(FS * 2)) / FS
    x = 0.8 * np.sin(2 * np.pi * 50 * t)
    _, envelope = EMGProcessor(FS, rms_window_s=0.1, highpass_hz=None).process(x)
    assert envelope[100:].mean() == pytest.approx(0.8 / np.sqrt(2), rel=0.02)


def test_streaming_matches_single_batch():
    x = EMGSimulator(scenario=Scenario.MODERATE).generate(3000).values
    _, whole = EMGProcessor(FS).process(x)
    streaming = EMGProcessor(FS)
    parts = [streaming.process(chunk)[1] for chunk in np.array_split(x, 37)]
    np.testing.assert_allclose(np.concatenate(parts), whole, atol=1e-12)


def test_highpass_removes_dc_offset():
    x = 2.0 + 0.01 * np.random.default_rng(0).standard_normal(int(FS * 3))
    filtered, envelope = EMGProcessor(FS).process(x)
    assert abs(filtered[-500:].mean()) < 0.01
    assert envelope[-1] < 0.05


def test_empty_batch():
    filtered, envelope = EMGProcessor(FS).process(np.empty(0))
    assert filtered.size == 0 and envelope.size == 0


# ------------------------------------------------------------------- detector
def test_sustained_pulse_counts_once_with_duration():
    t, a = square_pulse([(1.0, 0.0), (1.5, 0.6), (1.0, 0.0)])
    detector = ContractionDetector()
    events = detector.update(t, a)
    assert len(events) == 1
    assert events[0].duration == pytest.approx(1.5, abs=0.01)
    assert events[0].peak_activation == pytest.approx(0.6)
    assert detector.rejected_count == 0


def test_short_spike_is_rejected():
    t, a = square_pulse([(1.0, 0.0), (0.1, 0.9), (1.0, 0.0)])
    detector = ContractionDetector()
    assert detector.update(t, a) == []
    assert detector.rejected_count == 1


def test_hysteresis_ignores_wobble_between_thresholds():
    cfg = DetectorConfig(on_threshold=0.3, hysteresis=0.1)
    segments = [(0.5, 0.0), (0.4, 0.35)] + [(0.05, 0.25), (0.05, 0.35)] * 10 + [(0.5, 0.0)]
    t, a = square_pulse(segments)
    assert len(ContractionDetector(cfg).update(t, a)) == 1


def test_brief_dip_does_not_split_contraction():
    t, a = square_pulse([(0.5, 0.0), (0.8, 0.6), (0.1, 0.0), (0.8, 0.6), (0.5, 0.0)])
    events = ContractionDetector().update(t, a)
    assert len(events) == 1
    assert events[0].duration == pytest.approx(1.7, abs=0.01)


def test_two_separate_contractions():
    t, a = square_pulse([(0.5, 0.0), (0.8, 0.6), (1.0, 0.0), (0.8, 0.6), (0.5, 0.0)])
    assert len(ContractionDetector().update(t, a)) == 2


def test_bridged_spikes_are_not_confirmed():
    t, a = square_pulse([(0.5, 0.0), (0.1, 0.9), (0.15, 0.0), (0.1, 0.9), (0.5, 0.0)])
    detector = ContractionDetector()
    assert detector.update(t, a) == []
    assert detector.rejected_count == 1


def test_detection_is_independent_of_batch_size():
    t, a = square_pulse([(0.5, 0.0), (1.0, 0.6), (0.5, 0.0), (0.2, 0.8), (0.5, 0.0), (0.7, 0.5), (0.5, 0.0)])
    whole = ContractionDetector().update(t, a)
    chunked_detector = ContractionDetector()
    chunked = []
    for idx in np.array_split(np.arange(t.size), 23):
        chunked += chunked_detector.update(t[idx], a[idx])
    assert whole == chunked


def test_current_hold_tracks_open_contraction():
    detector = ContractionDetector()
    t, a = square_pulse([(0.5, 0.0), (1.2, 0.6)])
    detector.update(t, a)
    assert detector.is_active
    assert detector.current_hold() == pytest.approx(1.2, abs=0.01)


# --------------------------------------------------------- end-to-end pipeline
def test_rest_produces_no_contractions():
    events, detector = run_pipeline(EMGSimulator(scenario=Scenario.REST), 20)
    assert events == [] and not detector.above_threshold


@pytest.mark.parametrize("scenario", [Scenario.WEAK, Scenario.MODERATE])
def test_burst_scenarios_count_each_burst(scenario):
    events, _ = run_pipeline(EMGSimulator(scenario=scenario), 30)
    assert len(events) == 6
    assert all(1.5 < e.duration < 2.5 for e in events)


@pytest.mark.parametrize("seed", [1, 2, 3, 42])
def test_noisy_artifacts_are_not_counted(seed):
    events, detector = run_pipeline(EMGSimulator(scenario=Scenario.NOISY, seed=seed), 30)
    assert events == []
    assert detector.rejected_count > 0


@pytest.mark.parametrize("effort", [0.18, 0.22, 0.3])
def test_sustained_effort_near_threshold_is_one_contraction(effort):
    sim = EMGSimulator(seed=5)
    sim.manual_effort = effort
    events, detector = run_pipeline(sim, 15)
    assert len(events) + int(detector.is_active) <= 1
