"""Policy that takes no actions."""
from __future__ import annotations

from typing import TYPE_CHECKING

from agent0.base.policies import BasePolicy
from fixedpointmath import FixedPoint

from .base import MarketState, Wallet

if TYPE_CHECKING:
    from elfpy.types import Trade
    from numpy.random._generator import Generator as NumpyGenerator


# pylint: disable=too-few-public-methods


class NoActionPolicy(BasePolicy[MarketState, Wallet]):
    """NoOp class policy"""

    def __init__(self, budget: FixedPoint | None = None, rng: NumpyGenerator | None = None):
        if budget is None:
            super().__init__(FixedPoint("0.0"), rng)
        else:
            super().__init__(budget, rng)

    def action(self, market: MarketState, wallet: Wallet) -> list[Trade]:
        """Returns an empty list, indicating no action"""
        # pylint: disable=unused-argument
        return []
