"""Policy that takes no actions."""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from .base import BasePolicy, MarketInterface, Wallet

if TYPE_CHECKING:
    from elfpy.types import Trade
    from numpy.random._generator import Generator as NumpyGenerator


# pylint: disable=too-few-public-methods


class NoActionPolicy(BasePolicy[MarketInterface, Wallet]):
    """NoOp class policy"""

    def __init__(
        self,
        budget: FixedPoint | None = None,
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
    ):
        if budget is None:
            super().__init__(FixedPoint("0.0"), rng, slippage_tolerance)
        else:
            super().__init__(budget, rng, slippage_tolerance)

    def action(self, interface: MarketInterface, wallet: Wallet) -> list[Trade]:
        """Returns an empty list, indicating no action"""
        # pylint: disable=unused-argument
        return []
