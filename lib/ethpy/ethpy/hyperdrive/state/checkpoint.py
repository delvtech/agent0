"""Functions for storing Hyperdrive state."""
from __future__ import annotations

from dataclasses import dataclass

from fixedpointmath import FixedPoint


@dataclass
class Checkpoint:
    """Checkpoint struct."""

    share_price: FixedPoint
    exposure: FixedPoint
