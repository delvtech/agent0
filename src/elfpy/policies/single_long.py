"""
User strategy that opens a long position and then closes it after a certain amount of time has passed
"""
# pylint: disable=too-many-arguments

from elfpy.agent import Agent
from elfpy.markets import Market
from elfpy.types import MarketActionType


class Policy(Agent):
    """
    simple long
    only has one long open at a time
    """

    def __init__(self, wallet_address, budget=1000):
        """call basic policy init then add custom stuff"""
        self.amount_to_trade = 100
        super().__init__(wallet_address, budget)

    def action(self, market: Market):
        """Specify action"""
        can_open_long = (self.wallet.base >= self.amount_to_trade) and (
            market.market_state.share_reserves >= self.amount_to_trade
        )
        longs = list(self.wallet.longs.values())
        has_opened_long = bool(any((long.balance > 0 for long in longs)))
        action_list = []
        mint_times = list(self.wallet["longs"].keys())
        if has_opened_long:
            mint_time = mint_times[-1]
            enough_time_has_passed = market.time - mint_time > 0.25
            if enough_time_has_passed:
                action_list.append(
                    self.create_agent_action(
                        action_type=MarketActionType.CLOSE_LONG,
                        trade_amount=sum(long.balance for long in longs)
                        / (market.spot_price * 0.99),  # assume 1% slippage
                        mint_time=mint_time,
                    )
                )
        elif (not has_opened_long) and can_open_long:
            action_list.append(
                self.create_agent_action(action_type=MarketActionType.OPEN_LONG, trade_amount=self.amount_to_trade)
            )
        return action_list
