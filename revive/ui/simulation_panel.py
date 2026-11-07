"""Controls for the simulated EMG source (hidden when real hardware is connected)."""

from __future__ import annotations

from nicegui import ui

from revive.engine import ReViveEngine
from revive.sources.simulator import Scenario

HOLD_EFFORT = 0.7


def simulation_panel(engine: ReViveEngine, *, show_scenarios: bool) -> None:
    sim = engine.simulator
    if sim is None:
        return
    with ui.column().classes("revive-card w-full gap-3"):
        with ui.row().classes("w-full items-center justify-between"):
            ui.label("Simulation controls").classes("card-title")
            ui.label("SIMULATED DATA").classes("sim-badge")

        if show_scenarios:
            ui.label("Scenario").classes("text-sm font-semibold text-slate-700")
            scenario_name = ui.label(sim.scenario.label).classes("text-xs muted")

            def change_scenario(value: str) -> None:
                sim.set_scenario(value)
                scenario_name.set_text(sim.scenario.label)

            ui.toggle(
                {s.value: s.value.capitalize() for s in Scenario},
                value=sim.scenario.value,
                on_change=lambda e: change_scenario(e.value),
            ).props("spread no-caps rounded unelevated toggle-color=primary").classes("w-full")

        with ui.row().classes("w-full items-center gap-4 no-wrap"):
            ui.icon("tune", size="sm").classes("text-teal-700")
            with ui.column().classes("flex-grow gap-0"):
                ui.label("Simulated muscle effort").classes("text-sm font-semibold text-slate-700")
                ui.slider(min=0, max=1, step=0.01).bind_value(sim, "manual_effort").props("label color=primary")

        hold = ui.button("Press and hold to contract", icon="fitness_center").props("outline rounded no-caps size=lg")
        hold.classes("w-full")

        def press(_=None) -> None:
            sim.press_effort = HOLD_EFFORT

        def release(_=None) -> None:
            sim.press_effort = 0.0

        for event in ("mousedown", "touchstart"):
            hold.on(event, press)
        for event in ("mouseup", "mouseleave", "touchend", "touchcancel"):
            hold.on(event, release)
        ui.label(
            "Simulation lets you demonstrate ReVive without hardware. Values are generated, not measured."
        ).classes("text-xs muted")
