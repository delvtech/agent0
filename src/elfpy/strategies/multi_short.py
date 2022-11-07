"""
more complicated short
can have more than one short open at a time
"""


from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    User policy
    """
    def action(self):
        """specify action"""
        action_list = []
        can_open_short = self.get_max_short(self.market) > 10
        if can_open_short:
            action_list.append(["open_short", 10]) # open a short with 10 PT
        mint_times = list(self.wallet.keys()).pop("base")
        for token_mint_time in mint_times:
            enough_time_has_passed = self.market.time - token_mint_time >= 0.1
            if enough_time_has_passed: # 10 % of a year after mint
                action_list.append(["close_short", token_mint_time, 10])
        return action_list
