"""
User strategy that adds liquidity and then removes it when enough time has passed
"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments

from elfpy.policies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, market, rng, wallet_address, budget=1000):
        """call basic policy init then add custom stuff"""
        self.time_to_withdraw = self.rng.uniform(0.5, 1.5)
        self.amount_to_lp = 100
        super().__init__(
            market=market,
            rng=rng,
            wallet_address=wallet_address,
            budget=budget,
        )

    def action(self):
        """
        implement user strategy
        LP if you can, but only do it once
        """
        action_list = []
        has_lp = self.wallet.lp_in_wallet > 0
        can_lp = self.wallet.base_in_wallet >= self.amount_to_lp
        if not has_lp and can_lp:
            action_list.append(self.create_agent_action(action_type="add_liquidity", trade_amount=self.amount_to_lp))
        elif has_lp:
            enough_time_has_passed = self.market.time > self.time_to_withdraw
            if enough_time_has_passed:
                self.create_agent_action(action_type="remove_liquidity", trade_amount=self.wallet.lp_in_wallet)
        return action_list
