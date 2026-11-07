import pytest

from revive.core.exercises import ExerciseGoal, ExerciseSession, SessionState
from revive.core.signal_processing import Contraction


def rep(start: float, duration: float = 1.0) -> Contraction:
    return Contraction(start, start + duration, 0.5)


def test_contractions_only_count_while_running():
    session = ExerciseSession()
    assert not session.record(rep(0))
    session.start(now=1.0)
    assert session.record(rep(2))
    session.pause(now=4.0)
    assert not session.record(rep(5))
    assert session.reps == 1


def test_goal_completion():
    session = ExerciseSession(goal=ExerciseGoal(target_reps=2))
    session.start(0.0)
    session.record(rep(1, 1.0))
    assert session.state is SessionState.RUNNING
    session.record(rep(4, 2.0))
    assert session.state is SessionState.COMPLETE
    assert session.average_hold == pytest.approx(1.5)
    assert session.longest_hold == pytest.approx(2.0)
    assert session.elapsed(now=100.0) == pytest.approx(6.0)


def test_elapsed_excludes_paused_time():
    session = ExerciseSession()
    session.start(10.0)
    session.pause(15.0)
    assert session.elapsed(now=30.0) == pytest.approx(5.0)
    session.start(30.0)
    assert session.elapsed(now=32.0) == pytest.approx(7.0)


def test_reset_and_restart_after_completion():
    session = ExerciseSession(goal=ExerciseGoal(target_reps=1))
    session.start(0.0)
    session.record(rep(1))
    assert session.state is SessionState.COMPLETE
    session.start(10.0)
    assert session.state is SessionState.RUNNING and session.reps == 0
    session.reset()
    assert session.state is SessionState.IDLE and session.elapsed(50.0) == 0.0


def test_goal_description():
    assert ExerciseGoal(5).description == "Successfully activate your biceps 5 times"
    assert ExerciseGoal(1).description.endswith("1 time")
