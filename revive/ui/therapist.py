"""Physiotherapist dashboard: live signals, detection settings and session statistics."""

from __future__ import annotations

import numpy as np
from nicegui import ui

from revive.engine import ReViveEngine
from revive.ui.layout import BLUE, TEAL, format_clock, format_seconds, page_frame, set_text
from revive.ui.simulation_panel import simulation_panel

CHART_INTERVAL_S = 0.12
STATS_INTERVAL_S = 0.25
ACTIVATION_DECIMATION = 4


def _chart_options(color: str, y_axis: dict, area: bool = False) -> dict:
    series: dict = {
        "type": "line",
        "showSymbol": False,
        "data": [],
        "lineStyle": {"width": 1.2 if not area else 2, "color": color},
        "sampling": "lttb",
    }
    if area:
        series["areaStyle"] = {"color": color, "opacity": 0.12}
    return {
        "animation": False,
        "grid": {"left": 52, "right": 18, "top": 18, "bottom": 30},
        "xAxis": {
            "type": "value",
            "min": -ReViveEngine.history_s,
            "max": 0,
            "axisLabel": {"formatter": "{value} s", "color": "#64748b"},
            "splitLine": {"show": False},
        },
        "yAxis": {"axisLabel": {"color": "#64748b"}, "splitLine": {"lineStyle": {"color": "#eef2f6"}}, **y_axis},
        "series": [series],
    }


def _stat_card(title: str) -> ui.label:
    with ui.column().classes("revive-card gap-1 p-4"):
        ui.label(title).classes("card-title")
        return ui.label().classes("stat-number")


def build_therapist_page(engine: ReViveEngine) -> None:
    config = engine.detector.config
    with page_frame(engine, "therapist"):
        with ui.element("div").classes("grid grid-cols-2 md:grid-cols-3 xl:grid-cols-6 gap-4 w-full"):
            with ui.column().classes("revive-card gap-1 p-4"):
                ui.label("Signal source").classes("card-title")
                ui.label(engine.source.kind.value).classes("stat-number")
                ui.label(f"{engine.source.sample_rate:.0f} Hz").classes("text-xs muted")
            session_state = _stat_card("Session")
            attempts = _stat_card("Counted activations")
            rejected = _stat_card("Rejected (too short)")
            avg_hold = _stat_card("Average hold")
            elapsed = _stat_card("Session time")

        with ui.element("div").classes("grid grid-cols-1 xl:grid-cols-3 gap-5 w-full"):
            with ui.column().classes("xl:col-span-2 gap-5 w-full"):
                with ui.column().classes("revive-card w-full gap-1"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("Live EMG waveform (high-pass filtered)").classes("card-title")
                        if engine.source.is_simulated:
                            ui.label("SIMULATED").classes("sim-badge")
                    raw_chart = ui.echart(_chart_options(BLUE, {"scale": True, "name": "a.u."})).classes("w-full h-56")
                with ui.column().classes("revive-card w-full gap-1"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("Activation envelope (rolling RMS, normalised)").classes("card-title")
                        ui.label("— on threshold   ··· off threshold").classes("text-xs muted")
                    env_options = _chart_options(TEAL, {"min": 0, "max": 1.05}, area=True)
                    env_options["series"][0]["markLine"] = {"silent": True, "symbol": "none", "label": {"show": False}, "data": []}
                    env_chart = ui.echart(env_options).classes("w-full h-56")

                with ui.column().classes("revive-card w-full gap-2"):
                    ui.label("Contraction log").classes("card-title")
                    log_table = ui.table(
                        columns=[
                            {"name": "n", "label": "#", "field": "n", "align": "left"},
                            {"name": "start", "label": "Onset (s)", "field": "start", "align": "left"},
                            {"name": "duration", "label": "Hold duration", "field": "duration", "align": "left"},
                            {"name": "peak", "label": "Peak activation", "field": "peak", "align": "left"},
                        ],
                        rows=[],
                        row_key="n",
                    ).classes("w-full").props("flat dense")
                    ui.label(
                        "All confirmed contractions are logged; only those during a running session count toward the goal. "
                        "Peak activation is relative to calibration and is not a strength measure."
                    ).classes("text-xs muted")

            with ui.column().classes("gap-5 w-full"):
                with ui.column().classes("revive-card w-full gap-3"):
                    ui.label("Session").classes("card-title")
                    with ui.row().classes("w-full gap-2 no-wrap"):
                        start = ui.button("Start", icon="play_arrow", on_click=engine.start_session)
                        pause = ui.button("Pause", icon="pause", on_click=engine.pause_session, color="secondary")
                        reset = ui.button("Stop & reset", icon="stop", on_click=engine.reset_session, color="grey-7")
                        for b in (start, pause, reset):
                            b.classes("flex-grow").props("unelevated rounded no-caps")
                        reset.props("outline")

                with ui.column().classes("revive-card w-full gap-2"):
                    ui.label("Exercise & detection settings").classes("card-title")
                    ui.number(
                        "Goal: successful activations",
                        value=engine.session.goal.target_reps,
                        min=1,
                        max=50,
                        step=1,
                        precision=0,
                        on_change=lambda e: setattr(engine.session.goal, "target_reps", max(1, int(e.value or 1))),
                    ).classes("w-full").props("outlined dense")

                    def labelled_slider(label: str, obj: object, attr: str, lo: float, hi: float, step: float, fmt: str):
                        with ui.row().classes("w-full items-center justify-between mt-2"):
                            ui.label(label).classes("text-sm font-semibold text-slate-700")
                            ui.label().bind_text_from(obj, attr, backward=lambda v: fmt.format(v)).classes(
                                "text-sm font-bold text-teal-700"
                            )
                        ui.slider(min=lo, max=hi, step=step).bind_value(obj, attr)

                    labelled_slider("Activation threshold", config, "on_threshold", 0.05, 0.9, 0.01, "{:.0%}")
                    labelled_slider("Hysteresis band", config, "hysteresis", 0.0, 0.3, 0.01, "{:.0%}")
                    labelled_slider("Minimum contraction duration", config, "min_duration_s", 0.05, 2.0, 0.05, "{:.2f} s")
                    labelled_slider(
                        "Calibration reference level (a.u.)", engine.calibration, "reference_level", 0.2, 2.0, 0.05, "{:.2f}"
                    )
                    ui.label(
                        "Threshold and hysteresis are in normalised units (0 = rest, 100% = calibration reference). "
                        "Guided calibration arrives in Phase 2."
                    ).classes("text-xs muted")

                simulation_panel(engine, show_scenarios=True)

    def refresh_charts() -> None:
        if not engine.history_t:
            return
        t = np.fromiter(engine.history_t, float) - engine.now
        signal = np.fromiter(engine.history_signal, float)
        activation = np.fromiter(engine.history_activation, float)

        raw_chart.options["series"][0]["data"] = np.round(np.column_stack([t, signal]), 4).tolist()
        raw_chart.update()

        step = ACTIVATION_DECIMATION
        series = env_chart.options["series"][0]
        series["data"] = np.round(np.column_stack([t[::step], activation[::step]]), 4).tolist()
        series["markLine"]["data"] = [
            {"yAxis": round(config.on_threshold, 3), "lineStyle": {"color": "#0f172a", "type": "solid"}},
            {"yAxis": round(config.off_threshold, 3), "lineStyle": {"color": "#64748b", "type": "dotted"}},
        ]
        env_chart.update()

    seen = {"log": -1}

    def refresh_stats() -> None:
        session = engine.session
        set_text(session_state, session.state.value)
        set_text(attempts, f"{session.reps} / {session.goal.target_reps}")
        set_text(rejected, str(engine.session_rejected))
        set_text(avg_hold, format_seconds(session.average_hold))
        set_text(elapsed, format_clock(engine.session_elapsed))
        start.set_enabled(not session.is_running)
        pause.set_enabled(session.is_running)

        contractions = list(engine.recent_contractions)
        signature = hash(tuple((c.start, c.end) for c in contractions))
        if signature != seen["log"]:
            seen["log"] = signature
            log_table.rows = [
                {
                    "n": i + 1,
                    "start": f"{c.start:.1f}",
                    "duration": format_seconds(c.duration),
                    "peak": f"{c.peak_activation:.0%}",
                }
                for i, c in reversed(list(enumerate(contractions)))
            ][:12]

    ui.timer(CHART_INTERVAL_S, refresh_charts)
    ui.timer(STATS_INTERVAL_S, refresh_stats)
