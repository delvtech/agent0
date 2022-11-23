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
        amount_to_LP=100,
        pt_to_short=100,
        short_until_apr=0.05,
        verbose=False,
    ):
        """call basic policy init then add custom stuff"""
        self.amount_to_LP = amount_to_LP
        self.pt_to_short = pt_to_short
        self.short_until_apr = short_until_apr
        super().__init__(market=market, rng=rng, wallet_address=wallet_address, budget=budget, verbose=verbose)
        print(self.status_report())

    def action(self):
        """
        implement user strategy
        LP if you can, but only do it once
        short if you can, but only do it once
        """
        action_list = []
        if not self.has_LPd and self.can_LP:
            action_list.append(self.create_user_action(action_type="add_liquidity", trade_amount=self.amount_to_LP))
        if self.market.rate < self.short_until_apr and self.can_open_short:
            action_list.append(self.create_user_action(action_type="open_short", trade_amount=self.pt_to_short))
        return action_list
