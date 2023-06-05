"""Initialize a market with a desired amount of share & bond reserves"""
from __future__ import annotations

from typing import TYPE_CHECKING

from elfpy.markets.hyperdrive.hyperdrive_actions import HyperdriveMarketAction, MarketActionType
from elfpy.math import FixedPoint
from elfpy.types import Trade, MarketType

from .base import BasePolicy

if TYPE_CHECKING:
    from elfpy.wallet.wallet import Wallet
    from elfpy.markets.base.base_market import BaseMarket


# pylint: disable=too-few-public-methods
class InitializeLiquidityAgent(BasePolicy):
    """Adds a large LP"""

    def action(self, market: BaseMarket, wallet: Wallet) -> list[Trade]:
        """User strategy adds liquidity and then takes no additional actions"""
        if wallet.lp_tokens > FixedPoint(0):  # has already opened the lp
            return []
        return [
            Trade(
                market=MarketType.HYPERDRIVE,
                trade=HyperdriveMarketAction(
                    action_type=MarketActionType.ADD_LIQUIDITY,
                    trade_amount=self.budget,
                    wallet=wallet,
                ),
            )
        ]
