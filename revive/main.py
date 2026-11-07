"""ReVive entry point: ``python -m revive.main``."""

from __future__ import annotations

import os

from nicegui import app, ui

from revive.engine import ReViveEngine
from revive.ui.layout import install_theme
from revive.ui.patient import build_patient_page
from revive.ui.therapist import build_therapist_page

engine = ReViveEngine()
install_theme()


@ui.page("/", title="ReVive · Patient")
def patient_page() -> None:
    build_patient_page(engine)


@ui.page("/therapist", title="ReVive · Therapist")
def therapist_page() -> None:
    build_therapist_page(engine)


app.on_startup(engine.start)
app.on_shutdown(engine.stop)
app.timer(engine.tick_interval_s, engine.tick)


def main() -> None:
    ui.run(
        title="ReVive",
        host=os.environ.get("REVIVE_HOST", "127.0.0.1"),
        port=int(os.environ.get("REVIVE_PORT", "8080")),
        show=os.environ.get("REVIVE_NO_BROWSER") is None,
        reload=False,
        favicon="💪",
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
