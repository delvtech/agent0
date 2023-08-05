"""Base policy class

Policies inherit from Users (thus each policy is assigned to a user)
subclasses of BasicPolicy will implement trade actions
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from . import BasePolicy

if TYPE_CHECKING:
    from elfpy.markets.base import BaseMarket
    from elfpy.types import Trade
    from elfpy.wallet.wallet import Wallet
    from numpy.random._generator import Generator as NumpyGenerator

# pylint: disable=too-few-public-methods


class NoActionPolicy(BasePolicy):
    """NoOp class policy"""

    def __init__(self, budget: FixedPoint | None = None, rng: NumpyGenerator | None = None):
        if budget is None:
            super().__init__(FixedPoint("0.0"), rng)
        else:
            super().__init__(budget, rng)

    def action(self, market: BaseMarket, wallet: Wallet) -> list[Trade]:
        """Returns an empty list, indicating no action"""
        # pylint: disable=unused-argument
        return []
