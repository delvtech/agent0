"""User strategy that opens a single short and doesn't close until liquidation"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint
from lib.elfpy.elfpy.agents.policies.base import BasePolicy

from lib.elfpy.elfpy.markets.hyperdrive import HyperdriveMarketAction, MarketActionType
from lib.elfpy.elfpy.types import MarketType, Trade

if TYPE_CHECKING:
    from numpy.random._generator import Generator as NumpyGenerator

    from lib.elfpy.elfpy.markets.hyperdrive import HyperdriveMarket
    from lib.elfpy.elfpy.wallet.wallet import Wallet


# pylint: disable=too-few-public-methods


class SingleShortAgent(BasePolicy):
    """simple short thatonly has one long open at a time"""

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        budget: FixedPoint = FixedPoint("100.0"),
        rng: NumpyGenerator | None = None,
        slippage_tolerance: FixedPoint | None = None,
        amount_to_trade: FixedPoint | None = None,
    ):
        """call basic policy init then add custom stuff"""
        if amount_to_trade is None:
            amount_to_trade = budget
        self.amount_to_trade = amount_to_trade
        super().__init__(budget, rng, slippage_tolerance)

    def action(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """Implement user strategy: short if you can, only once."""
        action_list = []
        shorts = list(wallet.shorts.values())
        has_opened_short = len(shorts) > 0
        can_open_short = market.get_max_short_for_account(wallet.balance.amount) >= self.amount_to_trade
        if can_open_short and not has_opened_short:
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=MarketActionType.OPEN_SHORT,
                        trade_amount=self.amount_to_trade,
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                )
            )
        return action_list
