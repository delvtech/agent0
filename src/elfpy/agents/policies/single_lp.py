"""User strategy that adds base liquidity and doesn't remove until liquidation"""
from elfpy.agents.agent import Agent
from elfpy.markets.hyperdrive import Market, MarketActionType

# TODO: the init calls are replicated across each strategy, which looks like duplicate code
#     this should be resolved once we fix user inheritance
# issue #217
# pylint: disable=duplicate-code


class Policy(Agent):
    """simple LP that only has one LP open at a time"""

    def __init__(self, wallet_address, budget=1000):
        """call basic policy init then add custom stuff"""
        self.amount_to_lp = 100
        super().__init__(wallet_address, budget)

    def action(self, _market: Market):
        """
        implement user strategy
        LP if you can, but only do it once
        """
        action_list = []
        has_lp = self.wallet.lp_tokens > 0
        can_lp = self.wallet.base >= self.amount_to_lp
        if can_lp and not has_lp:
            action_list.append(
                self.create_agent_action(action_type=MarketActionType.ADD_LIQUIDITY, trade_amount=self.amount_to_lp)
            )
        return action_list
