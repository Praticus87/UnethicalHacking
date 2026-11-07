"""Common interface for anything that produces EMG samples.

The UI and processing pipeline only ever talk to a ``SignalSource``, so the
simulator can be swapped for real Arduino/BioAmp hardware without UI changes.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum

import numpy as np


class SourceKind(str, Enum):
    SIMULATION = "Simulation"
    ARDUINO = "Arduino"


@dataclass(frozen=True)
class SampleBatch:
    """A chunk of consecutive samples.

    ``timestamps`` are in seconds on the source's own clock and ``values`` are
    in source units (arbitrary units for the simulator, centred ADC units for
    hardware). Both arrays have the same length.
    """

    timestamps: np.ndarray
    values: np.ndarray

    def __post_init__(self) -> None:
        if self.timestamps.shape != self.values.shape:
            raise ValueError("timestamps and values must have the same shape")

    def __len__(self) -> int:
        return int(self.values.size)

    @classmethod
    def empty(cls) -> SampleBatch:
        return cls(np.empty(0), np.empty(0))


class SignalSource(ABC):
    """A pull-based stream of timestamped EMG samples."""

    kind: SourceKind
    sample_rate: float

    @property
    def is_simulated(self) -> bool:
        return self.kind is SourceKind.SIMULATION

    @property
    @abstractmethod
    def is_running(self) -> bool: ...

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def stop(self) -> None: ...

    @abstractmethod
    def read(self) -> SampleBatch:
        """Return all samples that became available since the previous call."""
