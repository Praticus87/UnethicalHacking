"""Placeholder for the Arduino UNO + BioAmp EXG Pill serial source (Phase 3).

Planned design: a background thread reads newline-delimited ADC samples from
the serial port with PySerial and queues them; ``read()`` drains the queue into
a ``SampleBatch``. The sampling rate, wire format and the BioAmp's on-board
filter configuration must be verified against the hardware documentation
before this is implemented.

Safety: only connect body electrodes when the laptop and Arduino are powered
by a manufacturer-approved, electrically safe and isolated setup (for example,
a battery-powered laptop that is not plugged into mains).
"""

from __future__ import annotations

from revive.sources.base import SampleBatch, SignalSource, SourceKind


class ArduinoSerialSource(SignalSource):
    kind = SourceKind.ARDUINO

    def __init__(self, port: str, baudrate: int = 115200, sample_rate: float = 500.0) -> None:
        self.port = port
        self.baudrate = baudrate
        self.sample_rate = sample_rate

    @property
    def is_running(self) -> bool:
        return False

    def start(self) -> None:
        raise NotImplementedError("Arduino acquisition is planned for Phase 3; use the simulator for now.")

    def stop(self) -> None:
        pass

    def read(self) -> SampleBatch:
        return SampleBatch.empty()
