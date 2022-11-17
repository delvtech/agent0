from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, market, rng, wallet_address, budget=1000, verbose=False):
        """call basic policy init then add custom stuff"""
        super().__init__(market=market, rng=rng, wallet_address=wallet_address, budget=budget, verbose=verbose)
        self.amount_to_trade = 100
        self.status_update()

    def action(self):
        """specify action"""
        self.status_update()
        action_list = []
        if not self.has_LPd and self.can_LP:
            action_list.append(["add_liquidity", self.amount_to_trade])
        return action_list

    def status_update(self):
        self.has_LPd = self.wallet["lp_in_wallet"] > 0
        self.can_LP = self.wallet["base_in_wallet"] >= self.amount_to_trade

    def status_report(self):
        return (
            f"has_LPd: {self.has_LPd}, can_LP: {self.can_LP}"
            + f" base_in_wallet: {self.wallet['base_in_wallet']}"
            + f" LP_position: {self.wallet['lp_in_wallet']}"
        )
