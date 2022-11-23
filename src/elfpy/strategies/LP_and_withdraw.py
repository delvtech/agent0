from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, market, rng, wallet_address, budget=1000, amount_to_LP=100, verbose=False):
        """call basic policy init then add custom stuff"""
        self.amount_to_LP = amount_to_LP
        self.time_to_withdraw = rng.uniform(0.5, 1.5)
        super().__init__(market=market, rng=rng, wallet_address=wallet_address, budget=budget, verbose=verbose)

    def action(self):
        """
        implement user strategy
        LP if you can, but only do it once
        """
        action_list = []
        if not self.has_LPd and self.can_LP:
            action_list.append(
                self.create_user_action(
                    action_type="add_liquidity",
                    trade_amount=self.amount_to_LP
                )
            )
        elif self.has_LPd:
            enough_time_has_passed = self.market.time > self.time_to_withdraw
            if enough_time_has_passed:
                self.create_user_action(
                        action_type="remove_liquidity",
                        trade_amount=self.wallet.lp_in_wallet
                )
        return action_list