"""Policy that takes no actions."""
from __future__ import annotations

from typing import TYPE_CHECKING

from agent0.base.policies import BasePolicy
from agent0.hyperdrive.agents import HyperdriveWallet

# from agent0.hyperdrive import HyperdriveMarketState  # FIXME: use agent0 market state instead of elfpy market
from elfpy.markets.hyperdrive import HyperdriveMarket as HyperdriveMarketState
from fixedpointmath import FixedPoint

if TYPE_CHECKING:
    from elfpy.types import Trade
    from numpy.random._generator import Generator as NumpyGenerator

# pylint: disable=too-few-public-methods


class NoActionPolicy(BasePolicy[HyperdriveMarketState, HyperdriveWallet]):
    """NoOp class policy"""

    def __init__(self, budget: FixedPoint | None = None, rng: NumpyGenerator | None = None):
        if budget is None:
            super().__init__(FixedPoint("0.0"), rng)
        else:
            super().__init__(budget, rng)

    def action(self, market: HyperdriveMarketState, wallet: HyperdriveWallet) -> list[Trade]:
        """Returns an empty list, indicating no action"""
        # pylint: disable=unused-argument
        return []
