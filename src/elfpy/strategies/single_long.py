from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple long
    only has one long open at a time
    """

    def __init__(self, market, rng, budget=1000, verbose=False):
        """call basic policy init then add custom stuff"""
        # self.position_list = []
        # self.has_opened_long = []
        # self.can_open_long = []
        super().__init__(market=market, rng=rng, verbose=verbose, budget=budget)
        self.amount_to_trade = 100
        self.status_update()

    def action(self):
        """specify action"""
        self.status_update()
        action_list = []
        mint_times = list(self.wallet["token_in_wallet"].keys())
        if self.has_opened_long:
            mint_time = mint_times[-1]
            enough_time_has_passed = self.market.time - mint_time > 0.5
            if enough_time_has_passed:
                action_list.append(["close_long", sum(self.position_list)*self.market.spot_price*0.995, mint_time])
        elif (not self.has_opened_long) and self.can_open_long:
            action_list.append(["open_long", self.amount_to_trade])
        return action_list

    def status_update(self):
        self.position_list = list(self.wallet["token_in_wallet"].values())
        self.has_opened_long = True if any([x > 1 for x in self.position_list]) else False
        self.can_open_long = self.get_max_long() >= self.amount_to_trade

    def status_report(self):
        return(
            f"has_opened_long: {self.has_opened_long}, can_open_long: {self.can_open_long}"+
            f" max_long: {self.get_max_long()}"+
            f" position_list: {self.position_list} sum(positions)={sum(self.position_list)}"
        )