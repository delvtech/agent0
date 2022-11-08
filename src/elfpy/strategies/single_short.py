"""
simple short
only has 1 short open at a time
"""


from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    User policy
    """
    def action(self):
        """specify action"""
        action_list = []
        mint_times = list(self.wallet.keys()).pop("base")
        has_opened_short = len(mint_times) == 1
        can_open_short = self.get_max_short(self.market) > 25
        if has_opened_short: # I have an open short
            enough_time_has_passed = self.market.time - mint_times[0] > 0.25
            if enough_time_has_passed:
                action_list.append(["close_short", 25, mint_times[0]]) # close a short with 25 PT
        elif not has_opened_short and can_open_short: # If I haven't done a short yet
            action_list.append(["open_short", 25]) # open a short with 25 PT
        return action_list
