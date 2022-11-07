class Policy:
    """
    simple short
    only has 1 short open at a time
    """
    def __init__(self, user, market):
        """comment"""
        self.user = user
        self.market = market

    def action(self):
        """specify action"""
        action_list = []
        mint_times = list(self.user.budget.keys()).pop("base")
        has_opened_short = len(mint_times) == 1
        can_open_short = self.user.get_max_short(self.market) > 25
        if has_opened_short: # I have an open short
            enough_time_has_passed = self.market.time - mint_times[0] > 0.25
            if enough_time_has_passed:
                action_list.append(["close_short", mint_times[0], 25]) # close a short with 25 PT
        elif not has_opened_short and can_open_short: # If I haven't done a short yet
            action_list.append(["open_short", 25]) # open a short with 25 PT
        return action_list
