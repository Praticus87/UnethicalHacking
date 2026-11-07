"""Repeatable simulated surface-EMG generator.

The model is intentionally simple but EMG-like:

* Muscle activity is band-limited Gaussian noise (20-150 Hz) whose amplitude
  follows a smooth "effort" envelope, so bursts look like real interference
  patterns rather than sine waves.
* A small broadband sensor-noise floor is always present.
* The "noisy" scenario adds short motion-artifact spikes and mains hum, which
  the processing pipeline should *not* count as contractions.

All randomness comes from a seeded ``numpy.random.Generator``, so the same
seed and the same sequence of ``generate()`` calls produce identical output.
Values are arbitrary units and must always be labelled as simulated data.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from enum import Enum

import numpy as np
from scipy import signal

from revive.sources.base import SampleBatch, SignalSource, SourceKind


class Scenario(str, Enum):
    REST = "rest"
    WEAK = "weak"
    MODERATE = "moderate"
    NOISY = "noisy"

    @property
    def label(self) -> str:
        return {
            Scenario.REST: "Resting muscle",
            Scenario.WEAK: "Weak contractions",
            Scenario.MODERATE: "Moderate contractions",
            Scenario.NOISY: "Noisy signal (artifacts)",
        }[self]


@dataclass(frozen=True)
class ScenarioProfile:
    burst_effort: float  # peak effort of automatic bursts (0 = no bursts)
    artifact_rate_hz: float = 0.0
    mains_hum: float = 0.0


PROFILES: dict[Scenario, ScenarioProfile] = {
    Scenario.REST: ScenarioProfile(burst_effort=0.0),
    Scenario.WEAK: ScenarioProfile(burst_effort=0.3),
    Scenario.MODERATE: ScenarioProfile(burst_effort=0.65),
    Scenario.NOISY: ScenarioProfile(burst_effort=0.0, artifact_rate_hz=0.6, mains_hum=0.01),
}

# Automatic burst protocol: ramp up, hold, ramp down, then rest.
CYCLE_S = 5.0
RAMP_S = 0.3
HOLD_S = 1.6
BURST_START_S = 1.0

MAX_BATCH_S = 0.5


class EMGSimulator(SignalSource):
    kind = SourceKind.SIMULATION

    def __init__(
        self,
        sample_rate: float = 500.0,
        seed: int = 42,
        scenario: Scenario = Scenario.REST,
        noise_floor: float = 0.012,
        muscle_gain: float = 1.0,
        effort_time_constant_s: float = 0.08,
    ) -> None:
        self.sample_rate = float(sample_rate)
        self.seed = seed
        self.scenario = scenario
        self.noise_floor = noise_floor
        self.muscle_gain = muscle_gain
        self._manual_effort = 0.0
        self.press_effort = 0.0  # momentary effort from a press-and-hold control

        nyquist = self.sample_rate / 2
        high = min(150.0, 0.9 * nyquist)
        self._band_sos = signal.butter(4, [20.0, high], btype="bandpass", fs=self.sample_rate, output="sos")
        # The band-pass loses power; this restores roughly unit RMS for unit-variance input.
        self._band_gain = 1.0 / np.sqrt((high - 20.0) / nyquist)
        alpha = 1.0 - np.exp(-1.0 / (effort_time_constant_s * self.sample_rate))
        self._effort_b = np.array([alpha])
        self._effort_a = np.array([1.0, alpha - 1.0])

        self._running = False
        self.reset()

    def reset(self) -> None:
        """Restart the deterministic sample stream from t = 0."""
        self._rng = np.random.default_rng(self.seed)
        self._band_zi = np.zeros((self._band_sos.shape[0], 2))
        self._effort_zi = np.zeros(1)
        self._sample_index = 0
        self._artifacts: list[tuple[float, float]] = []  # (onset time, signed amplitude)
        self._last_wall: float | None = None
        self._carry = 0.0

    # ----------------------------------------------------------------- control
    @property
    def manual_effort(self) -> float:
        return self._manual_effort

    @manual_effort.setter
    def manual_effort(self, value: float) -> None:
        self._manual_effort = float(np.clip(value, 0.0, 1.0))

    def set_scenario(self, scenario: Scenario | str) -> None:
        self.scenario = Scenario(scenario)
        self._artifacts.clear()

    # --------------------------------------------------------- SignalSource API
    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        self._running = True
        self._last_wall = time.monotonic()
        self._carry = 0.0

    def stop(self) -> None:
        self._running = False
        self._last_wall = None

    def read(self) -> SampleBatch:
        """Generate the samples that would have arrived since the last read (real time)."""
        if not self._running or self._last_wall is None:
            return SampleBatch.empty()
        now = time.monotonic()
        elapsed = min(now - self._last_wall, MAX_BATCH_S)
        self._last_wall = now
        exact = elapsed * self.sample_rate + self._carry
        n = int(exact)
        self._carry = exact - n
        return self.generate(n)

    # -------------------------------------------------------------- generation
    def generate(self, n: int) -> SampleBatch:
        """Generate the next ``n`` samples, independent of wall-clock time."""
        if n <= 0:
            return SampleBatch.empty()
        idx = np.arange(self._sample_index, self._sample_index + n)
        t = idx / self.sample_rate
        self._sample_index += n
        profile = PROFILES[self.scenario]

        user_effort = max(self._manual_effort, self.press_effort)
        target = np.maximum(self._burst_effort(t, profile.burst_effort), user_effort)
        effort, self._effort_zi = signal.lfilter(self._effort_b, self._effort_a, target, zi=self._effort_zi)

        white = self._rng.standard_normal(n)
        carrier, self._band_zi = signal.sosfilt(self._band_sos, white, zi=self._band_zi)
        carrier *= self._band_gain

        values = self.muscle_gain * effort * carrier
        values += self.noise_floor * self._rng.standard_normal(n)
        if profile.mains_hum:
            values += profile.mains_hum * np.sin(2 * np.pi * 60.0 * t)
        if profile.artifact_rate_hz:
            values += self._artifact_signal(t, profile.artifact_rate_hz)

        return SampleBatch(timestamps=t, values=values)

    def _burst_effort(self, t: np.ndarray, peak: float) -> np.ndarray:
        if peak <= 0:
            return np.zeros_like(t)
        cycle = np.floor(t / CYCLE_S).astype(int)
        phase = t - cycle * CYCLE_S - BURST_START_S
        # Each burst varies slightly in strength, deterministically per cycle.
        variation = 1.0 + 0.15 * np.sin(1.7 * cycle + 0.3 * self.seed)
        rise = np.clip(phase / RAMP_S, 0.0, 1.0)
        fall = np.clip((RAMP_S + HOLD_S + RAMP_S - phase) / RAMP_S, 0.0, 1.0)
        shape = np.minimum(rise, fall)
        return peak * variation * shape

    def _artifact_signal(self, t: np.ndarray, rate_hz: float) -> np.ndarray:
        """Short, decaying spikes resembling cable or electrode motion artifacts."""
        onsets = np.flatnonzero(self._rng.random(t.size) < rate_hz / self.sample_rate)
        for i in onsets:
            amplitude = self._rng.uniform(1.2, 2.5) * self._rng.choice([-1.0, 1.0])
            self._artifacts.append((float(t[i]), float(amplitude)))

        out = np.zeros_like(t)
        tau = 0.015
        kept: list[tuple[float, float]] = []
        for onset, amplitude in self._artifacts:
            dt = t - onset
            active = dt >= 0
            out[active] += amplitude * np.exp(-dt[active] / tau) * np.cos(2 * np.pi * 35.0 * dt[active])
            if t[-1] - onset < 10 * tau:
                kept.append((onset, amplitude))
        self._artifacts = kept
        return out
