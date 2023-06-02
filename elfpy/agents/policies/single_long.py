"""User strategy that opens a long position and then closes it after a certain amount of time has passed"""
from __future__ import annotations

from elfpy.agents.agent import Agent
from elfpy.math import FixedPoint
from elfpy.markets.hyperdrive.hyperdrive_actions import HyperdriveMarketAction, MarketActionType
from elfpy.markets.hyperdrive.hyperdrive_market import Market as HyperdriveMarket
from elfpy.types import Trade, MarketType


class SingleLongAgent(Agent):
    """
    simple long
    only has one long open at a time
    """

    def action(self, market: HyperdriveMarket) -> list[Trade]:
        """Specify action"""
        longs = list(self.wallet.longs.values())
        has_opened_long = len(longs) > 0
        action_list = []
        if has_opened_long:
            mint_time = list(self.wallet.longs)[-1]
            enough_time_has_passed = market.block_time.time - mint_time > FixedPoint("0.01")
            if enough_time_has_passed:
                action_list.append(
                    Trade(
                        market=MarketType.HYPERDRIVE,
                        trade=HyperdriveMarketAction(
                            action_type=MarketActionType.CLOSE_LONG,
                            trade_amount=longs[-1].balance,
                            wallet=self.wallet,
                            mint_time=mint_time,
                        ),
                    )
                )
        else:
            trade_amount = self.get_max_long(market) / FixedPoint("2.0")
            action_list.append(
                Trade(
                    market=MarketType.HYPERDRIVE,
                    trade=HyperdriveMarketAction(
                        action_type=MarketActionType.OPEN_LONG,
                        trade_amount=trade_amount,
                        wallet=self.wallet,
                    ),
                )
            )
        return action_list
