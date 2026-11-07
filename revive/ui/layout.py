"""Shared look and feel: theme CSS, header navigation and small UI helpers."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from nicegui import ui

from revive.engine import ReViveEngine

TEAL = "#0d9488"
BLUE = "#2563eb"

CSS = """
body { background: #f2f7f9; color: #0f172a; }
.revive-header { background: rgba(255,255,255,0.92); backdrop-filter: blur(8px);
  border-bottom: 1px solid #e2ecf0; color: #0f172a; }
.revive-card { background: #fff; border-radius: 20px; border: 1px solid #e3edf1;
  box-shadow: 0 1px 2px rgba(15,23,42,.04), 0 10px 28px rgba(15,23,42,.06); padding: 1.4rem; }
.card-title { font-size: 0.8rem; font-weight: 700; letter-spacing: .08em; text-transform: uppercase; color: #64748b; }
.big-number { font-size: 3.2rem; line-height: 1; font-weight: 800; color: #0f172a; font-variant-numeric: tabular-nums; }
.stat-number { font-size: 1.9rem; line-height: 1.1; font-weight: 750; color: #0f172a; font-variant-numeric: tabular-nums; }
.muted { color: #64748b; }
.sim-badge { background: #fff7ed; color: #b45309; border: 1px solid #fed7aa; border-radius: 999px;
  padding: 4px 12px; font-size: .78rem; font-weight: 700; letter-spacing: .04em; }
.hw-badge { background: #ecfdf5; color: #047857; border: 1px solid #a7f3d0; border-radius: 999px;
  padding: 4px 12px; font-size: .78rem; font-weight: 700; letter-spacing: .04em; }
.status-pill { border-radius: 999px; padding: 10px 20px; font-size: 1.15rem; font-weight: 700;
  transition: background-color 150ms, color 150ms; display: inline-flex; align-items: center; gap: 8px; }
.status-idle { background: #f1f5f9; color: #475569; }
.status-active { background: #ccfbf1; color: #0f766e; }
.meter-track { position: relative; height: 30px; border-radius: 15px; background: #e6f0f3; overflow: hidden; }
.meter-fill { height: 100%; width: var(--level, 0%); border-radius: 15px;
  background: linear-gradient(90deg, #5eead4, #0d9488); transition: width 70ms linear; }
.meter-threshold { position: absolute; top: 0; bottom: 0; left: var(--threshold, 20%); width: 3px; background: #0f172a; opacity: .7; }
.progress-dot { width: 22px; height: 22px; border-radius: 50%; background: #e2e8f0; transition: background-color 200ms, transform 200ms; }
.progress-dot.done { background: #0d9488; transform: scale(1.1); }
.goal-banner { background: linear-gradient(90deg, #ccfbf1, #dbeafe); color: #0f766e; border-radius: 14px;
  padding: 10px 14px; font-weight: 700; font-size: 1.05rem; }
.disclaimer { font-size: .8rem; color: #94a3b8; text-align: center; }
"""

LOGO_SVG = """
<svg width="38" height="38" viewBox="0 0 40 40" aria-hidden="true">
  <rect width="40" height="40" rx="12" fill="#0d9488"/>
  <path d="M6 22 H13 L16 13 L21 29 L25 17 L27 22 H34" fill="none" stroke="#fff" stroke-width="3"
        stroke-linecap="round" stroke-linejoin="round"/>
</svg>
"""

DISCLAIMER = (
    "ReVive is a research and educational prototype, not a medical device. "
    "EMG activation shown here is a biofeedback cue: it does not measure strength, "
    "prove neurological recovery or predict return of movement."
)


def install_theme() -> None:
    ui.add_head_html(f"<style>{CSS}</style>", shared=True)


def source_badge(engine: ReViveEngine) -> None:
    if engine.source.is_simulated:
        ui.label("SIMULATED DATA").classes("sim-badge")
    else:
        ui.label(f"{engine.source.kind.value.upper()} · LIVE").classes("hw-badge")


@contextmanager
def page_frame(engine: ReViveEngine, active: str) -> Iterator[None]:
    ui.colors(primary=TEAL, secondary=BLUE, positive="#10b981", warning="#f59e0b")
    with ui.header().classes("revive-header px-6 py-3 items-center"):
        with ui.row().classes("items-center gap-3 no-wrap"):
            ui.html(LOGO_SVG, sanitize=False)
            with ui.column().classes("gap-0"):
                ui.label("ReVive").classes("text-2xl font-extrabold text-slate-900 leading-none")
                ui.label("EMG biofeedback rehabilitation").classes("text-xs muted")
        ui.space()
        with ui.row().classes("items-center gap-2"):
            source_badge(engine)
            for key, label, icon, target in (
                ("patient", "Patient", "accessibility_new", "/"),
                ("therapist", "Therapist", "monitor_heart", "/therapist"),
            ):
                button = ui.button(label, icon=icon, on_click=lambda t=target: ui.navigate.to(t))
                button.props("unelevated rounded no-caps" if key == active else "flat rounded no-caps")
    with ui.column().classes("w-full max-w-7xl mx-auto px-4 md:px-6 py-6 gap-5"):
        yield
        ui.label(DISCLAIMER).classes("disclaimer w-full mt-2")


def set_text(label: ui.label, text: str) -> None:
    """Only push a text change to the browser when the text actually changed."""
    if label.text != text:
        label.set_text(text)


def format_seconds(seconds: float) -> str:
    return f"{seconds:.1f} s"


def format_clock(seconds: float) -> str:
    minutes, secs = divmod(int(seconds), 60)
    return f"{minutes:02d}:{secs:02d}"
