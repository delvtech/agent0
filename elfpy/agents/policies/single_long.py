"""User strategy that opens a long position and then closes it after a certain amount of time has passed"""
from __future__ import annotations

from typing import TYPE_CHECKING

from elfpy.math import FixedPoint, FixedPointMath
from elfpy.markets.hyperdrive.hyperdrive_actions import HyperdriveMarketAction, MarketActionType
from elfpy.types import Trade, MarketType

from .base import BasePolicy

if TYPE_CHECKING:
    from elfpy.agents.wallet import Wallet
    from elfpy.markets.base.base_market import BaseMarket

# pylint: disable=too-few-public-methods


class SingleLongAgent(BasePolicy):
    """
    simple long
    only has one long open at a time
    """

    def action(self, market: BaseMarket, wallet: Wallet) -> list[Trade]:
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
                        market=MarketType.HYPERDRIVE,
                        trade=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_LONG,
                            trade_amount=longs[-1].balance,
                            wallet=wallet,
                            mint_time=mint_time,
                        ),
                    )
                )
        else:
            max_base, _ = market.pricing_model.get_max_long(
                market_state=market.market_state, time_remaining=market.position_duration
            )
            max_long = min(wallet.balance.amount, max_base)
            trade_amount = max_long / FixedPoint("2.0")
            action_list.append(
                Trade(
                    market=MarketType.HYPERDRIVE,
                    trade=HyperdriveMarketAction(
                        action_type=MarketActionType.OPEN_LONG,
                        trade_amount=trade_amount,
                        wallet=wallet,
                    ),
                )
            )
        return action_list
