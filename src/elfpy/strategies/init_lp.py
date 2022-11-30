"""
Special reserved user strategy that is used to initialize a market with a desired amount of share & bond reserves
"""
# pylint: disable=duplicate-code

from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(
        self,
        market,
        rng,
        wallet_address,
        budget=1000,
        verbose=None,
        amount_to_lp=100,
        pt_to_short=100,
        short_until_apr=0.05,
    ):
        """call basic policy init then add custom stuff"""
        self.amount_to_lp = amount_to_lp
        self.pt_to_short = pt_to_short
        self.short_until_apr = short_until_apr
        self.is_lp = True
        self.is_shorter = True
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
        short if you can, but only do it once
        """
        action_list = []
        if not self.has_lp and self.can_lp:
            action_list.append(self.create_agent_action(action_type="add_liquidity", trade_amount=self.amount_to_lp))
        if self.market.rate < self.short_until_apr and self.can_open_short:
            action_list.append(self.create_agent_action(action_type="open_short", trade_amount=self.pt_to_short))
        return action_list
