class Policy:
    """
    simple long
    only has one long open at a time
    """
    def __init__(self, user, market):
        """comment"""
        self.user = user
        self.market = market
        self.last_long_time = -1

    def action(self):
        """specify action"""
        action_list = []
        has_opened_long = self.last_long_time > 0
        can_open_long = self.user.get_max_long() >= 100
        enough_time_has_passed = self.market.time - self.last_long_time > 0.25
        if has_opened_long and can_open_long:
            action_list.append(["open_long", 100])
            self.last_long_time = self.market.time
        elif enough_time_has_passed:
            action_list.append(["close_long", 100])
            self.last_long_time = -1
        return action_list

        

        return action_list
