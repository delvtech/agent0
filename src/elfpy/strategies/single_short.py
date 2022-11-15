from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple short
    only has one long open at a time
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
        if self.has_opened_short:
            mint_time = self.mint_times[-1]
            enough_time_has_passed = self.market.time - mint_time > 0.25
            if enough_time_has_passed:
                action_list.append(
                    self.UserAction(
                        action_type="close_short",
                        trade_amount=self.wallet["token_in_wallet"][mint_time],
                        mint_time=mint_time,
                    )
                )
        elif (not self.has_opened_short) and self.can_open_short:
            action_list.append(self.UserAction(action_type="open_short", trade_amount=self.amount_to_trade))
        return action_list

    def status_update(self):
        self.position_list = list(self.wallet["token_in_wallet"].values())
        self.mint_times = list(self.wallet["token_in_wallet"].keys())
        self.has_opened_short = True if any([x < -1 for x in self.position_list]) else False
        self.can_open_short = self.get_max_short(self.market.time) >= self.amount_to_trade

    def status_report(self):
        return (
            f"has_opened_short: {self.has_opened_short}, can_open_short: {self.can_open_short}"
            + f" max_short: {self.get_max_short(self.market.time)}"
            + f" position_list: {self.position_list} sum(positions)={sum(self.position_list)}"
        )
