from __future__ import annotations
from dataclasses import dataclass, field
from elfpy import FixedPoint

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

    def share_price_default():
        return FixedPoint(0)

    def long_share_price_default():
        return FixedPoint(0)

    def long_base_volume_default():
        return FixedPoint(0)

    def short_base_volume_default():
        return FixedPoint(0)

    share_price: FixedPoint = field(default_factory=share_price_default)
    long_share_price: FixedPoint = field(default_factory=long_share_price_default)
    long_base_volume: FixedPoint = field(default_factory=long_base_volume_default)
    short_base_volume: FixedPoint = field(default_factory=short_base_volume_default)

# all values zeroed
DEFAULT_CHECKPOINT = Checkpoint()
