"""Patient-specific normalisation of the EMG envelope.

Normalised activation maps the resting level to 0 and a reference level (for
example the patient's best comfortable attempt during calibration) to 1. It is
a display/biofeedback scale only: it does not represent force, strength or
neurological recovery, and values are not comparable between patients.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class Calibration:
    rest_level: float = 0.015
    reference_level: float = 1.0

    def __post_init__(self) -> None:
        if self.reference_level <= self.rest_level:
            raise ValueError("reference_level must be greater than rest_level")

    def normalize(self, envelope: np.ndarray) -> np.ndarray:
        span = self.reference_level - self.rest_level
        return np.clip((np.asarray(envelope, dtype=float) - self.rest_level) / span, 0.0, 1.0)

    @classmethod
    def from_recordings(cls, rest_envelope: np.ndarray, reference_envelope: np.ndarray) -> Calibration:
        return cls(
            rest_level=estimate_rest_level(rest_envelope),
            reference_level=estimate_reference_level(reference_envelope),
        )


def estimate_rest_level(envelope: np.ndarray, percentile: float = 75.0) -> float:
    """Resting baseline from an envelope recorded while the patient relaxes.

    A high-ish percentile keeps ordinary resting fluctuations at or below 0.
    """
    envelope = np.asarray(envelope, dtype=float)
    if envelope.size == 0:
        raise ValueError("cannot estimate a baseline from an empty recording")
    return float(np.percentile(envelope, percentile))


def estimate_reference_level(envelope: np.ndarray, percentile: float = 95.0) -> float:
    """Reference activation from an envelope recorded during contraction attempts."""
    envelope = np.asarray(envelope, dtype=float)
    if envelope.size == 0:
        raise ValueError("cannot estimate a reference from an empty recording")
    return float(np.percentile(envelope, percentile))
