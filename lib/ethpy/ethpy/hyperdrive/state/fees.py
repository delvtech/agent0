"""Functions for storing Hyperdrive state."""
from __future__ import annotations

from dataclasses import dataclass

from fixedpointmath import FixedPoint


@dataclass
class Fees:
    """Fees struct."""

    curve: FixedPoint
    flat: FixedPoint
    governance: FixedPoint
