"""
User strategy that adds liquidity and then removes it when enough time has passed
"""
# pylint: disable=duplicate-code

from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, market, rng, wallet_address, budget=1000, verbose=None, amount_to_lp=100):
        """call basic policy init then add custom stuff"""
        self.time_to_withdraw = self.rng.uniform(0.5, 1.5)
        self.amount_to_lp = amount_to_lp
        self.is_lp = True
        self.is_shorter = False
        super().__init__(
            market=market,
            rng=rng,
            wallet_address=wallet_address,
            budget=budget,
            verbose=verbose,
        )

    def action(self):
        """
        implement user strategy
        LP if you can, but only do it once
        """
        action_list = []
        if not self.has_lp and self.can_lp:
            action_list.append(self.create_agent_action(action_type="add_liquidity", trade_amount=self.amount_to_lp))
        elif self.has_lp:
            enough_time_has_passed = self.market.time > self.time_to_withdraw
            if enough_time_has_passed:
                self.create_agent_action(action_type="remove_liquidity", trade_amount=self.wallet.lp_in_wallet)
        return action_list
