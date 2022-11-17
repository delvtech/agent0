from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple long
    only has one long open at a time
    """

    def __init__(self, market, rng, budget=1000, verbose=False):
        """call basic policy init then add custom stuff"""
        super().__init__(market=market, rng=rng, budget=budget, verbose=verbose)
        self.amount_to_trade = 100
        self.status_update()

    def action(self):
        """specify action"""
        self.status_update()
        action_list = []
        mint_times = list(self.wallet["token_in_wallet"].keys())
        if self.has_opened_long:
            mint_time = mint_times[-1]
            enough_time_has_passed = self.market.time - mint_time > 0.25
            if enough_time_has_passed:
                action_list.append(
                    self.UserAction(
                        action_type="close_long",
                        trade_amount=sum(self.position_list) / (self.market.spot_price * 0.99),  # assume 1% slippage
                        mint_time=mint_time
                    )
                )
        elif (not self.has_opened_long) and self.can_open_long:
            action_list.append(
                self.UserAction(
                    action_type="open_long",
                    trade_amount=self.amount_to_trade
                )
            )
        return action_list

    def status_update(self):
        """Update user conditionals"""
        self.position_list = list(self.wallet["token_in_wallet"].values())
        self.has_opened_long = True if any([x > 1 for x in self.position_list]) else False
        self.can_open_long = self.get_max_long() >= self.amount_to_trade

    def status_report(self):
        """Report state of user conditionals"""
        return (
            f"has_opened_long: {self.has_opened_long}, can_open_long: {self.can_open_long}"
            + f" max_long: {self.get_max_long()}"
            + f" position_list: {self.position_list} sum(positions)={sum(self.position_list)}"
        )
