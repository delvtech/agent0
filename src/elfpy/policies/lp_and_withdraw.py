"""
User strategy that adds liquidity and then removes it when enough time has passed
"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments

from elfpy.agent import Agent
from elfpy.markets import Market
from elfpy.pricing_models.base import PricingModel
from elfpy.types import MarketActionType


class Policy(Agent):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, wallet_address, budget=1000):
        """call basic policy init then add custom stuff"""
        self.time_to_withdraw = 1.0
        self.amount_to_lp = 100
        super().__init__(wallet_address, budget)

    def action(self, market: Market, _pricing_model: PricingModel):
        """
        implement user strategy
        LP if you can, but only do it once
        """
        # pylint disable=unused-argument
        action_list = []
        has_lp = self.wallet.lp > 0
        can_lp = self.wallet.base >= self.amount_to_lp
        if not has_lp and can_lp:
            action_list.append(
                self.create_agent_action(action_type=MarketActionType.ADD_LIQUIDITY, trade_amount=self.amount_to_lp)
            )
        elif has_lp:
            enough_time_has_passed = market.time > self.time_to_withdraw
            if enough_time_has_passed:
                self.create_agent_action(
                    action_type=MarketActionType.REMOVE_LIQUIDITY, trade_amount=self.wallet.lp
                )
        return action_list
