"""
User strategy that adds liquidity and then removes it when enough time has passed
"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments

from elfpy.markets import Market
from elfpy.pricing_models import PricingModel
from elfpy.policies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, wallet_address, budget=1000):
        """call basic policy init then add custom stuff"""
        self.time_to_withdraw = 1.0
        self.amount_to_lp = 100
        super().__init__(wallet_address, budget)

    def action(self, market: Market, pricing_model: PricingModel):
        """
        implement user strategy
        LP if you can, but only do it once
        """
        # pylint disable=unused-argument
        action_list = []
        has_lp = self.wallet.lp_in_wallet > 0
        can_lp = self.wallet.base_in_wallet >= self.amount_to_lp
        if not has_lp and can_lp:
            action_list.append(self.create_agent_action(action_type="add_liquidity", trade_amount=self.amount_to_lp))
        elif has_lp:
            enough_time_has_passed = market.time > self.time_to_withdraw
            if enough_time_has_passed:
                self.create_agent_action(action_type="remove_liquidity", trade_amount=self.wallet.lp_in_wallet)
        return action_list
