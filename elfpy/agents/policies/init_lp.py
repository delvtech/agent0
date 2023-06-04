"""Initialize a market with a desired amount of share & bond reserves"""
from __future__ import annotations

from typing import TYPE_CHECKING

from elfpy.agents.policies import BasePolicy
from elfpy.markets.hyperdrive.hyperdrive_actions import HyperdriveMarketAction, MarketActionType
from elfpy.math import FixedPoint
from elfpy.types import Trade, MarketType

if TYPE_CHECKING:
    from elfpy.agents.wallet import Wallet
    from elfpy.markets.hyperdrive.hyperdrive_market import Market as HyperdriveMarket


# pylint: disable=too-few-public-methods
class InitializeLiquidityAgent(BasePolicy):
    """Adds a large LP"""

    def action(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
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
