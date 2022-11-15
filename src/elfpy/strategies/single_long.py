from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple long
    only has one long open at a time
    """

    def __init__(self, market, rng, verbose=False):
        """call basic policy init then add custom stuff"""
        budget = 1000
        super().__init__(market=market, rng=rng, verbose=verbose, budget=budget)

    def action(self):
        """specify action"""
        action_list = []
        amount_to_trade = 100
        mint_times = list(self.wallet["token_in_wallet"].keys())
        has_opened_long = len(mint_times) > 0
        can_open_long = self.get_max_long() >= amount_to_trade
        if has_opened_long:
            mint_time = mint_times[0]
            enough_time_has_passed = self.market.time - mint_time > 0.25
            if enough_time_has_passed:
                action_list.append(["close_long", amount_to_trade, mint_time])
        elif (not has_opened_long) and can_open_long:
            action_list.append(["open_long", amount_to_trade])
        return action_list
