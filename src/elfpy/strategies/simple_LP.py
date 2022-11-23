from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, market, rng, wallet_address, budget=1000, amount_to_LP=100, verbose=False):
        """call basic policy init then add custom stuff"""
        self.amount_to_LP = amount_to_LP
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
        return action_list

