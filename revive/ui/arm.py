"""Animated 2D virtual arm (side view).

The upper arm is fixed; the forearm group rotates about the elbow. Python only
sets two CSS custom properties (forearm angle and activation level); the
browser interpolates between updates with a short CSS transition, which keeps
the animation smooth without streaming SVG.

The forearm angle is a visual cue, not the patient's real elbow angle.
"""

from __future__ import annotations

from nicegui import ui

REST_ANGLE_DEG = 22.0  # forearm slightly below horizontal (screen rotation, clockwise positive)
FLEXED_ANGLE_DEG = -66.0
ELBOW = (175, 290)
HAND_RADIUS = 232

ARM_SVG = f"""
<svg viewBox="0 0 520 430" class="w-full h-auto" role="img"
     aria-label="Virtual arm driven by muscle activation">
  <defs>
    <linearGradient id="skin" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="#e3eef3"/><stop offset="1" stop-color="#c9dde5"/>
    </linearGradient>
    <radialGradient id="muscle" cx="0.4" cy="0.4" r="0.7">
      <stop offset="0" stop-color="#5eead4"/><stop offset="1" stop-color="#0d9488"/>
    </radialGradient>
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="8"/>
    </filter>
  </defs>
  <style>
    .forearm {{ transform: rotate(var(--forearm-angle, {REST_ANGLE_DEG}deg)); transform-origin: 0 0;
                transition: transform 60ms linear; }}
    .biceps {{ fill-opacity: calc(0.22 + var(--activation, 0) * 0.78);
               transform: scale(calc(1 + var(--activation, 0) * 0.12)); transform-origin: 0 0;
               transition: fill-opacity 80ms linear, transform 80ms linear; }}
    .biceps-glow {{ opacity: calc(var(--activation, 0) * 0.8); transition: opacity 80ms linear; }}
    .goal-ring {{ opacity: calc(0.35 + var(--goal, 0) * 0.65); transition: opacity 150ms; }}
  </style>

  <!-- range-of-motion guide and goal marker -->
  <path d="M 390.1 376.9 A {HAND_RADIUS} {HAND_RADIUS} 0 0 0 269.4 78.1"
        fill="none" stroke="#cbd5e1" stroke-width="3" stroke-dasharray="4 10" stroke-linecap="round"/>
  <g class="goal-ring">
    <circle cx="269.4" cy="78.1" r="24" fill="#ccfbf1" stroke="#14b8a6" stroke-width="3"/>
    <path d="M258.7 78.7 l7 7 l13 -15" fill="none" stroke="#0d9488" stroke-width="4"
          stroke-linecap="round" stroke-linejoin="round"/>
  </g>

  <!-- torso -->
  <rect x="30" y="30" width="110" height="380" rx="48" fill="#eaf2f5"/>

  <!-- upper arm (stationary) -->
  <line x1="150" y1="92" x2="{ELBOW[0]}" y2="{ELBOW[1]}" stroke="url(#skin)" stroke-width="72" stroke-linecap="round"/>
  <g transform="translate(184 188) rotate(7)">
    <ellipse class="biceps-glow" rx="34" ry="70" fill="#2dd4bf" filter="url(#glow)"/>
    <ellipse class="biceps" rx="26" ry="62" fill="url(#muscle)"/>
  </g>
  <circle cx="150" cy="92" r="40" fill="#d6e6ec"/>

  <!-- forearm (rotates about the elbow) -->
  <g transform="translate({ELBOW[0]} {ELBOW[1]})">
    <g class="forearm">
      <path d="M 0 -29 L 205 -19 Q 214 0 205 19 L 0 29 Z" fill="url(#skin)"/>
      <ellipse cx="{HAND_RADIUS}" cy="0" rx="30" ry="23" fill="#c9dde5"/>
      <ellipse cx="{HAND_RADIUS + 6}" cy="-16" rx="16" ry="9" fill="#bcd3dc"/>
    </g>
    <circle r="31" fill="#d6e6ec"/>
    <circle r="9" fill="#94b4c1"/>
  </g>
</svg>
"""


class VirtualArm:
    def __init__(self) -> None:
        self.container = ui.element("div").classes("w-full max-w-xl mx-auto")
        with self.container:
            ui.html(ARM_SVG, sanitize=False).classes("w-full")
        self._last: tuple[float, float, int] | None = None

    def set_state(self, flex: float, activation: float) -> None:
        flex = min(1.0, max(0.0, flex))
        angle = REST_ANGLE_DEG + (FLEXED_ANGLE_DEG - REST_ANGLE_DEG) * flex
        state = (round(angle, 1), round(activation, 2), int(flex > 0.85))
        if state == self._last:
            return
        self._last = state
        self.container.style(f"--forearm-angle: {state[0]}deg; --activation: {state[1]}; --goal: {state[2]}")
