"""User strategy that opens a long position and then closes it after a certain amount of time has passed"""
from __future__ import annotations

from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint

from elfpy.markets.hyperdrive import HyperdriveMarketAction, MarketActionType
from elfpy.types import MarketType, Trade

from .base import BasePolicy

if TYPE_CHECKING:
    from elfpy.markets.hyperdrive import HyperdriveMarket
    from elfpy.wallet.wallet import Wallet

# pylint: disable=too-few-public-methods


class SingleLongAgent(BasePolicy):
    """
    simple long
    only has one long open at a time
    """

    def action(self, market: HyperdriveMarket, wallet: Wallet) -> list[Trade]:
        """Specify action"""
        longs = list(wallet.longs.values())
        has_opened_long = len(longs) > 0
        action_list = []
        if has_opened_long:
            mint_time = list(wallet.longs)[-1]
            enough_time_has_passed = market.block_time.time - mint_time > FixedPoint("0.01")
            if enough_time_has_passed:
                action_list.append(
                    Trade(
                        market_type=MarketType.HYPERDRIVE,
                        market_action=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_LONG,
                            trade_amount=longs[-1].balance,
                            slippage_tolerance=self.slippage_tolerance,
                            wallet=wallet,
                            mint_time=mint_time,
                        ),
                    )
                )
        else:
            trade_amount = market.get_max_long_for_account(wallet.balance.amount)
            action_list.append(
                Trade(
                    market_type=MarketType.HYPERDRIVE,
                    market_action=HyperdriveMarketAction(
                        action_type=MarketActionType.OPEN_LONG,
                        trade_amount=trade_amount,
                        slippage_tolerance=self.slippage_tolerance,
                        wallet=wallet,
                    ),
                )
            )
        return action_list
