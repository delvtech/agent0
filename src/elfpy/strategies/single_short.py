"""
simple short
only has 1 short open at a time
"""


from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    User policy
    """

    def __init__(self, market, rng, verbose=False):
        """call basic policy init then add custom stuff"""
        budget = 1000
        super().__init__(market=market, rng=rng, verbose=verbose, budget=budget)

    def action(self):
        """specify action"""
        amount_to_trade = 100
        action_list = []
        mint_times = list(self.wallet["base_in_protocol"].keys())
        has_opened_short = True if any([x < 0 for x in list(self.wallet['token_in_wallet'].values())]) else False
        if has_opened_short:
            mint_time = mint_times[0]
            enough_time_has_passed = self.market.time - mint_time > 0.25
            if enough_time_has_passed:
                action_list.append(["close_short", amount_to_trade, mint_time])  # close a short with 25 PT
        else:  # has not opened a short position
            mint_time = self.market.time
            can_open_short = self.get_max_short(mint_time) > amount_to_trade
            if can_open_short:
                action_list.append(["open_short", amount_to_trade])  # open a short with 25 PT
        return action_list
