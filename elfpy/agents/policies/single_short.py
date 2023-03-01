"""User strategy that opens a single short and doesn't close until liquidation"""
from elfpy.agents.agent import Agent
import elfpy.markets.hyperdrive as hyperdrive
import elfpy.types as types

# pylint: disable=duplicate-code


class Policy(Agent):
    """simple short thatonly has one long open at a time"""

    def __init__(self, wallet_address, budget=100):
        """call basic policy init then add custom stuff"""
        self.amount_to_trade = 100
        super().__init__(wallet_address, budget)

    def action(self, market: hyperdrive.Market) -> "list[types.Trade]":
        """
        implement user strategy
        short if you can, only once
        """
        action_list = []
        shorts = list(self.wallet.shorts.values())
        has_opened_short = len(shorts) > 0
        can_open_short = self.get_max_short(market) >= self.amount_to_trade
        if can_open_short and not has_opened_short:
            action_list.append(
                types.Trade(
                    market=types.MarketType.HYPERDRIVE,
                    trade=hyperdrive.MarketAction(
                        action_type=hyperdrive.MarketActionType.OPEN_SHORT,
                        trade_amount=self.amount_to_trade,
                        wallet=self.wallet,
                    ),
                )
            )
        return action_list
