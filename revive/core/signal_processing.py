"""EMG envelope extraction and contraction detection.

Pipeline per batch of samples:

1. Optional high-pass filter to remove DC offset and slow drift. The default
   (20 Hz, 2nd-order Butterworth) is a placeholder: the right filter depends
   on the sampling rate and on the BioAmp EXG Pill's verified on-board
   filtering, so it is configurable and should be re-checked in Phase 3.
2. Rolling RMS envelope over a short window (default 100 ms).
3. The envelope is normalised by a ``Calibration`` (see calibration.py).
4. ``ContractionDetector`` applies hysteresis and a minimum duration so that
   brief artifacts and noise do not count as voluntary activations.

The envelope reflects electrical activity at the electrodes. It is not a
measure of force or strength.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy import signal


class EMGProcessor:
    """Stateful, streaming rolling-RMS envelope extractor."""

    def __init__(self, sample_rate: float, rms_window_s: float = 0.1, highpass_hz: float | None = 20.0) -> None:
        self.sample_rate = float(sample_rate)
        self.window = max(1, int(round(rms_window_s * self.sample_rate)))
        self.highpass_hz = highpass_hz
        self._sos = (
            signal.butter(2, highpass_hz, btype="highpass", fs=self.sample_rate, output="sos")
            if highpass_hz
            else None
        )
        self.reset()

    def reset(self) -> None:
        self._zi = np.zeros((self._sos.shape[0], 2)) if self._sos is not None else None
        self._tail = np.zeros(self.window - 1)

    def filter(self, values: np.ndarray) -> np.ndarray:
        if self._sos is None:
            return np.asarray(values, dtype=float)
        filtered, self._zi = signal.sosfilt(self._sos, values, zi=self._zi)
        return filtered

    def process(self, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Return ``(filtered_signal, rms_envelope)`` for a batch, one value per input sample."""
        values = np.asarray(values, dtype=float)
        if values.size == 0:
            return values, values
        filtered = self.filter(values)
        squared = np.concatenate([self._tail, filtered**2])
        cumulative = np.concatenate([[0.0], np.cumsum(squared)])
        mean_square = (cumulative[self.window :] - cumulative[: -self.window]) / self.window
        if self.window > 1:
            self._tail = squared[-(self.window - 1) :]
        return filtered, np.sqrt(np.maximum(mean_square, 0.0))


@dataclass
class DetectorConfig:
    """Thresholds are in normalised activation units (0 = rest, 1 = calibration reference)."""

    on_threshold: float = 0.2
    hysteresis: float = 0.07
    min_duration_s: float = 0.3
    min_release_s: float = 0.25

    @property
    def off_threshold(self) -> float:
        return max(0.0, self.on_threshold - self.hysteresis)


@dataclass(frozen=True)
class Contraction:
    start: float
    end: float
    peak_activation: float

    @property
    def duration(self) -> float:
        return self.end - self.start


class ContractionDetector:
    """Hysteresis state machine that turns an activation trace into contraction events.

    * Activation rising above ``on_threshold`` opens a *candidate*.
    * The candidate stays open while activation remains above ``off_threshold``.
    * Once activation has stayed continuously above ``off_threshold`` for
      ``min_duration_s`` the candidate is *confirmed* (a real activation).
    * The candidate ends once activation has stayed below ``off_threshold`` for
      ``min_release_s``, so brief dips during a sustained effort do not split it
      into several repetitions. A confirmed candidate is emitted as a
      ``Contraction`` ending at the first sample of the dip; an unconfirmed one
      is counted as rejected.
    """

    def __init__(self, config: DetectorConfig | None = None) -> None:
        self.config = config or DetectorConfig()
        self.reset()

    def reset(self) -> None:
        self.above_threshold = False
        self.confirmed = False
        self.onset_time: float | None = None
        self.release_time: float | None = None
        self._segment_start = 0.0
        self.peak = 0.0
        self.rejected_count = 0
        self.last_time = 0.0

    @property
    def is_active(self) -> bool:
        """True while a confirmed contraction is in progress."""
        return self.above_threshold and self.confirmed

    def current_hold(self) -> float:
        if not self.above_threshold or self.onset_time is None:
            return 0.0
        end = self.release_time if self.release_time is not None else self.last_time
        return end - self.onset_time

    def update(self, timestamps: np.ndarray, activation: np.ndarray) -> list[Contraction]:
        events: list[Contraction] = []
        cfg = self.config
        for t, a in zip(timestamps.tolist(), activation.tolist()):
            self.last_time = t
            if not self.above_threshold:
                if a >= cfg.on_threshold:
                    self.above_threshold = True
                    self.confirmed = False
                    self.onset_time = t
                    self._segment_start = t
                    self.release_time = None
                    self.peak = a
                continue

            if a < cfg.off_threshold:
                if self.release_time is None:
                    self.release_time = t
                if t - self.release_time < cfg.min_release_s:
                    continue
                if self.confirmed and self.onset_time is not None:
                    events.append(Contraction(self.onset_time, self.release_time, self.peak))
                else:
                    self.rejected_count += 1
                self.above_threshold = False
                self.confirmed = False
                self.onset_time = None
                self.release_time = None
                self.peak = 0.0
                continue

            if self.release_time is not None:
                self.release_time = None
                self._segment_start = t
            self.peak = max(self.peak, a)
            if not self.confirmed and t - self._segment_start >= cfg.min_duration_s:
                self.confirmed = True
        return events
