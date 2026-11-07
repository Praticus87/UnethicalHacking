from revive.core.exercises import SessionState
from revive.engine import ReViveEngine
from revive.sources.simulator import EMGSimulator, Scenario


def run(engine: ReViveEngine, seconds: float, chunk: int = 10) -> None:
    sim = engine.simulator
    assert sim is not None
    for _ in range(int(seconds * sim.sample_rate / chunk)):
        engine.process(sim.generate(chunk))


def test_arm_rests_without_activation():
    engine = ReViveEngine(EMGSimulator(scenario=Scenario.REST))
    run(engine, 3)
    assert engine.arm_flex < 0.01
    assert not engine.detector.is_active


def test_arm_flexes_with_strong_effort_and_returns():
    engine = ReViveEngine(EMGSimulator())
    engine.simulator.manual_effort = 0.9
    run(engine, 2)
    assert engine.arm_flex > 0.7
    assert engine.detector.is_active
    engine.simulator.manual_effort = 0.0
    run(engine, 2)
    assert engine.arm_flex < 0.05


def test_session_counts_simulated_bursts():
    engine = ReViveEngine(EMGSimulator(scenario=Scenario.MODERATE))
    engine.start_session()
    run(engine, 26)
    assert engine.session.state is SessionState.COMPLETE
    assert engine.session.reps == 5
    assert engine.last_hold > 1.5


def test_history_is_bounded_and_reset_clears_session():
    engine = ReViveEngine(EMGSimulator(scenario=Scenario.MODERATE))
    engine.start_session()
    run(engine, 10)
    assert len(engine.history_t) == engine.history_t.maxlen
    engine.reset_session()
    assert engine.session.reps == 0 and not engine.recent_contractions
