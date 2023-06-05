"""User strategy that adds base liquidity and doesn't remove until liquidation"""
from __future__ import annotations

from typing import TYPE_CHECKING

from elfpy.markets.hyperdrive.hyperdrive_actions import HyperdriveMarketAction, MarketActionType
from elfpy.math import FixedPoint
from elfpy.types import MarketType, Trade

from .base import BasePolicy

if TYPE_CHECKING:
    from numpy.random._generator import Generator as NumpyGenerator

    from elfpy.agents.wallet import Wallet
    from elfpy.markets.base.base_market import BaseMarket

# pylint: disable=too-few-public-methods


class SingleLpAgent(BasePolicy):
    """simple LP that only has one LP open at a time"""

    def __init__(
        self,
        budget: FixedPoint = FixedPoint("1000.0"),
        rng: NumpyGenerator | None = None,
        amount_to_lp: FixedPoint = FixedPoint("100.0"),
    ):
        """call basic policy init then add custom stuff"""
        self.amount_to_lp: FixedPoint = amount_to_lp
        super().__init__(budget, rng)

    def action(self, market: BaseMarket, wallet: Wallet) -> list[Trade]:
        """
        implement user strategy
        LP if you can, but only do it once
        """
        action_list = []
        has_lp = wallet.lp_tokens > FixedPoint(0)
        can_lp = wallet.balance.amount >= self.amount_to_lp
        if can_lp and not has_lp:
            action_list.append(
                Trade(
                    market=MarketType.HYPERDRIVE,
                    trade=HyperdriveMarketAction(
                        action_type=MarketActionType.ADD_LIQUIDITY,
                        trade_amount=self.amount_to_lp,
                        wallet=wallet,
                    ),
                )
            )
        return action_list
