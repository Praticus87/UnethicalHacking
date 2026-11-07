"""Exercise session state: goal, repetitions and timing."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from revive.core.signal_processing import Contraction


class SessionState(str, Enum):
    IDLE = "Ready"
    RUNNING = "In progress"
    PAUSED = "Paused"
    COMPLETE = "Goal reached"


@dataclass
class ExerciseGoal:
    target_reps: int = 5

    @property
    def description(self) -> str:
        noun = "time" if self.target_reps == 1 else "times"
        return f"Successfully activate your biceps {self.target_reps} {noun}"


@dataclass
class ExerciseSession:
    """Counts contractions only while the session is running.

    Time is measured on the signal source's clock so that sessions are
    reproducible with the simulator.
    """

    goal: ExerciseGoal = field(default_factory=ExerciseGoal)
    state: SessionState = SessionState.IDLE
    contractions: list[Contraction] = field(default_factory=list)
    _active_elapsed: float = 0.0
    _resumed_at: float | None = None

    @property
    def reps(self) -> int:
        return len(self.contractions)

    @property
    def is_running(self) -> bool:
        return self.state is SessionState.RUNNING

    @property
    def average_hold(self) -> float:
        if not self.contractions:
            return 0.0
        return sum(c.duration for c in self.contractions) / len(self.contractions)

    @property
    def longest_hold(self) -> float:
        return max((c.duration for c in self.contractions), default=0.0)

    def elapsed(self, now: float) -> float:
        if self._resumed_at is None:
            return self._active_elapsed
        return self._active_elapsed + max(0.0, now - self._resumed_at)

    def start(self, now: float) -> None:
        if self.state is SessionState.COMPLETE:
            self.reset()
        if self.state is not SessionState.RUNNING:
            self.state = SessionState.RUNNING
            self._resumed_at = now

    def pause(self, now: float) -> None:
        if self.state is SessionState.RUNNING:
            self._active_elapsed = self.elapsed(now)
            self._resumed_at = None
            self.state = SessionState.PAUSED

    def reset(self) -> None:
        self.state = SessionState.IDLE
        self.contractions.clear()
        self._active_elapsed = 0.0
        self._resumed_at = None

    def record(self, contraction: Contraction) -> bool:
        """Add a contraction if the session is running. Returns True if it was counted."""
        if not self.is_running:
            return False
        self.contractions.append(contraction)
        if self.reps >= self.goal.target_reps:
            self._active_elapsed = self.elapsed(contraction.end)
            self._resumed_at = None
            self.state = SessionState.COMPLETE
        return True
