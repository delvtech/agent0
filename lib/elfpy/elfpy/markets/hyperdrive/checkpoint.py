"""Checkpoint Class for a Hyperdrive Market."""
from __future__ import annotations

from dataclasses import dataclass

from fixedpointmath import FixedPoint


@dataclass
class Checkpoint:
    """
    Hyperdrive positions are bucketed into checkpoints, which allows us to avoid poking in any
    period that has LP or trading activity. The checkpoints contain the starting share price from
    the checkpoint as well as aggregate volume values.
    """

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)

    share_price: FixedPoint = FixedPoint(0)
    long_share_price: FixedPoint = FixedPoint(0)
    long_base_volume: FixedPoint = FixedPoint(0)
    short_base_volume: FixedPoint = FixedPoint(0)


# all values zeroed
DEFAULT_CHECKPOINT = Checkpoint()
