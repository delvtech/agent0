"""Initialize a market with a desired amount of share & bond reserves"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint
from lib.elfpy.elfpy.agents.policies.base import BasePolicy

from lib.elfpy.elfpy.markets.hyperdrive import HyperdriveMarketAction, MarketActionType
from lib.elfpy.elfpy.types import MarketType, Trade

if TYPE_CHECKING:
    from lib.elfpy.elfpy.markets.base import BaseMarket
    from lib.elfpy.elfpy.wallet.wallet import Wallet


class InitializeLiquidityAgent(BasePolicy):
    """Adds a large LP"""

    def action(self, market: BaseMarket, wallet: Wallet) -> list[Trade]:
        """User strategy adds liquidity and then takes no additional actions"""
        if wallet.lp_tokens > FixedPoint(0):  # has already opened the lp
            return []
        return [
            Trade(
                market_type=MarketType.HYPERDRIVE,
                market_action=HyperdriveMarketAction(
                    action_type=MarketActionType.ADD_LIQUIDITY,
                    trade_amount=self.budget,
                    slippage_tolerance=self.slippage_tolerance,
                    wallet=wallet,
                ),
            )
        ]
