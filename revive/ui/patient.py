"""Patient-facing biofeedback screen: big virtual arm, simple goal and feedback."""

from __future__ import annotations

from nicegui import ui

from revive.core.exercises import SessionState
from revive.engine import ReViveEngine
from revive.ui.arm import VirtualArm
from revive.ui.layout import format_clock, format_seconds, page_frame, set_text
from revive.ui.simulation_panel import simulation_panel

UPDATE_INTERVAL_S = 1 / 30


def build_patient_page(engine: ReViveEngine) -> None:
    with page_frame(engine, "patient"):
        with ui.element("div").classes("grid grid-cols-1 lg:grid-cols-5 gap-5 w-full"):
            with ui.column().classes("revive-card lg:col-span-3 items-center gap-3"):
                with ui.row().classes("w-full items-center justify-between"):
                    ui.label("Virtual arm").classes("card-title")
                    status = ui.label().classes("status-pill status-idle")
                arm = VirtualArm()
                ui.label(
                    "The virtual arm moves when muscle activity rises above your threshold. "
                    "It is a visual cue, not your actual elbow angle."
                ).classes("text-sm muted text-center")

            with ui.column().classes("lg:col-span-2 gap-5 w-full"):
                with ui.column().classes("revive-card w-full gap-3"):
                    ui.label("Today's exercise").classes("card-title")
                    objective = ui.label().classes("text-xl font-semibold text-slate-800")
                    with ui.row().classes("items-end gap-2"):
                        reps = ui.label().classes("big-number")
                        reps_goal = ui.label().classes("text-2xl font-semibold muted pb-1")
                    dots_row = ui.row().classes("gap-2")
                    banner = ui.label("Goal reached! Great work.").classes("goal-banner w-full")
                    with ui.row().classes("w-full justify-between text-sm muted"):
                        state_label = ui.label()
                        elapsed = ui.label()

                with ui.element("div").classes("grid grid-cols-2 gap-5 w-full"):
                    with ui.column().classes("revive-card gap-1"):
                        ui.label("Current hold").classes("card-title")
                        hold = ui.label().classes("stat-number")
                    with ui.column().classes("revive-card gap-1"):
                        ui.label("Last hold").classes("card-title")
                        last_hold = ui.label().classes("stat-number")

                with ui.column().classes("revive-card w-full gap-2"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("Muscle activation").classes("card-title")
                        level = ui.label().classes("text-lg font-bold text-teal-700")
                    meter = ui.element("div").classes("meter-track w-full")
                    with meter:
                        ui.element("div").classes("meter-fill")
                        ui.element("div").classes("meter-threshold")
                    ui.label("Black line = your activation threshold").classes("text-xs muted")

                with ui.row().classes("w-full gap-3 no-wrap"):
                    start = ui.button("Start", icon="play_arrow", on_click=engine.start_session)
                    pause = ui.button("Pause", icon="pause", on_click=engine.pause_session, color="secondary")
                    reset = ui.button("Reset", icon="restart_alt", on_click=engine.reset_session, color="grey-7")
                    for b in (start, pause, reset):
                        b.classes("flex-grow").props("unelevated size=lg rounded no-caps")
                    reset.props("outline")

        simulation_panel(engine, show_scenarios=False)

    seen: dict = {"reps": -1, "target": -1, "meter": "", "active": None, "state": None}

    def refresh() -> None:
        session = engine.session
        detector = engine.detector
        arm.set_state(engine.arm_flex, engine.activation)

        active = detector.is_active
        if active != seen["active"]:
            seen["active"] = active
            status.set_text("✓ Activation detected" if active else "Relaxed – try to contract")
            status.classes(replace="status-pill " + ("status-active" if active else "status-idle"))

        target = session.goal.target_reps
        set_text(objective, session.goal.description)
        set_text(reps, str(session.reps))
        set_text(reps_goal, f"/ {target}")
        if (session.reps, target) != (seen["reps"], seen["target"]):
            if 0 < session.reps and session.reps > seen["reps"] >= 0:
                ui.notify(f"Activation {session.reps} counted!", type="positive", position="top")
            seen["reps"], seen["target"] = session.reps, target
            dots_row.clear()
            with dots_row:
                for i in range(target):
                    ui.element("div").classes("progress-dot" + (" done" if i < session.reps else ""))
        set_text(state_label, f"Session: {session.state.value}")
        set_text(elapsed, f"Time {format_clock(engine.session_elapsed)}")

        set_text(hold, format_seconds(engine.current_hold))
        set_text(last_hold, format_seconds(engine.last_hold))

        set_text(level, f"{engine.activation * 100:.0f}%")
        meter_style = f"--level: {engine.activation * 100:.1f}%; --threshold: {detector.config.on_threshold * 100:.1f}%"
        if meter_style != seen["meter"]:
            seen["meter"] = meter_style
            meter.style(meter_style)

        if session.state != seen["state"]:
            seen["state"] = session.state
            running = session.state is SessionState.RUNNING
            start.set_text("Resume" if session.state is SessionState.PAUSED else "Start")
            start.set_enabled(not running)
            pause.set_enabled(running)
            banner.set_visibility(session.state is SessionState.COMPLETE)

    ui.timer(UPDATE_INTERVAL_S, refresh)
