"""Smoke tests for the NiceGUI pages using NiceGUI's simulated user (no browser needed)."""

import pytest
from nicegui.testing import User

pytestmark = pytest.mark.asyncio


async def test_patient_page_renders(user: User) -> None:
    await user.open("/")
    await user.should_see("Virtual arm")
    await user.should_see("Successfully activate your biceps 5 times")
    await user.should_see("SIMULATED DATA")
    await user.should_see("Press and hold to contract")


async def test_patient_start_button_starts_session(user: User) -> None:
    await user.open("/")
    user.find("Start").click()
    await user.should_see("Session: In progress")


async def test_therapist_page_renders(user: User) -> None:
    await user.open("/therapist")
    await user.should_see("Live EMG waveform (high-pass filtered)")
    await user.should_see("Activation threshold")
    await user.should_see("Contraction log")
    await user.should_see("Simulation")
