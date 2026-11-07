"""Runtime that connects a signal source to processing, detection and the exercise session.

One engine instance is shared by every browser tab, so the patient screen and
the therapist dashboard always show the same live session.
"""

from __future__ import annotations

import math
from collections import deque

import numpy as np

from revive.core.calibration import Calibration
from revive.core.exercises import ExerciseSession
from revive.core.signal_processing import Contraction, ContractionDetector, EMGProcessor
from revive.sources.base import SampleBatch, SignalSource
from revive.sources.simulator import EMGSimulator

ARM_SMOOTHING_S = 0.12


class ReViveEngine:
    tick_interval_s = 0.02
    history_s = 6.0

    def __init__(self, source: SignalSource | None = None) -> None:
        self.source = source or EMGSimulator()
        self.processor = EMGProcessor(self.source.sample_rate)
        self.calibration = Calibration()
        self.detector = ContractionDetector()
        self.session = ExerciseSession()

        size = int(self.history_s * self.source.sample_rate)
        self.history_t: deque[float] = deque(maxlen=size)
        self.history_signal: deque[float] = deque(maxlen=size)
        self.history_activation: deque[float] = deque(maxlen=size)
        self.recent_contractions: deque[Contraction] = deque(maxlen=50)

        self.now = 0.0
        self.activation = 0.0
        self.arm_flex = 0.0  # 0 = resting pose, 1 = fully flexed virtual arm
        self.session_rejected = 0

    @property
    def simulator(self) -> EMGSimulator | None:
        return self.source if isinstance(self.source, EMGSimulator) else None

    # ------------------------------------------------------------------ runtime
    def start(self) -> None:
        if not self.source.is_running:
            self.source.start()

    def stop(self) -> None:
        self.source.stop()

    def tick(self) -> None:
        self.process(self.source.read())

    def process(self, batch: SampleBatch) -> list[Contraction]:
        if len(batch) == 0:
            return []
        filtered, envelope = self.processor.process(batch.values)
        activation = self.calibration.normalize(envelope)

        rejected_before = self.detector.rejected_count
        events = self.detector.update(batch.timestamps, activation)
        if self.session.is_running:
            self.session_rejected += self.detector.rejected_count - rejected_before
        for event in events:
            self.recent_contractions.append(event)
            self.session.record(event)

        dt = float(batch.timestamps[-1] - self.now) if self.history_t else 0.0
        self.now = float(batch.timestamps[-1])
        self.activation = float(activation[-1])
        self.history_t.extend(batch.timestamps.tolist())
        self.history_signal.extend(filtered.tolist())
        self.history_activation.extend(activation.tolist())
        self._update_arm(dt)
        return events

    def _update_arm(self, dt: float) -> None:
        threshold = self.detector.config.on_threshold
        target = 0.0
        if self.detector.above_threshold:
            target = float(np.clip((self.activation - threshold) / max(1e-6, 1.0 - threshold), 0.0, 1.0))
        alpha = 1.0 - math.exp(-max(dt, 0.0) / ARM_SMOOTHING_S)
        self.arm_flex += (target - self.arm_flex) * alpha

    # ----------------------------------------------------------- session control
    def start_session(self) -> None:
        self.session.start(self.now)

    def pause_session(self) -> None:
        self.session.pause(self.now)

    def reset_session(self) -> None:
        self.session.reset()
        self.session_rejected = 0
        self.recent_contractions.clear()

    @property
    def session_elapsed(self) -> float:
        return self.session.elapsed(self.now)

    @property
    def current_hold(self) -> float:
        return self.detector.current_hold()

    @property
    def last_hold(self) -> float:
        return self.recent_contractions[-1].duration if self.recent_contractions else 0.0
