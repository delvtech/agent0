"""User strategy that opens a long position and then closes it after a certain amount of time has passed"""

from elfpy.agents.agent import Agent
from elfpy.markets.hyperdrive import Market, MarketActionType
import elfpy.types as types

# pylint: disable=too-many-arguments


class Policy(Agent):
    """
    simple long
    only has one long open at a time
    """

    def action(self, market: Market) -> "list[types.Trade]":
        """Specify action"""
        longs = list(self.wallet.longs.values())
        has_opened_long = bool(any((long.balance > 0 for long in longs)))
        action_list = []
        if has_opened_long:
            mint_time = list(self.wallet.longs)[-1]
            enough_time_has_passed = market.time - mint_time > 0.01
            if enough_time_has_passed:
                action_list.append(
                    self.create_hyperdrive_action(
                        action_type=MarketActionType.CLOSE_LONG,
                        trade_amount=longs[-1].balance,
                        mint_time=mint_time,
                    )
                )
        else:
            trade_amount = self.get_max_long(market) / 2
            action_list.append(
                self.create_hyperdrive_action(action_type=MarketActionType.OPEN_LONG, trade_amount=trade_amount)
            )
        action_list = [types.Trade(market=types.MarketType.HYPERDRIVE, trade=trade) for trade in action_list]
        return action_list
