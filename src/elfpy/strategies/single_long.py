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
        self.last_long_time = -1

    def action(self):
        """specify action"""
        action_list = []
        has_opened_long = self.last_long_time > 0
        can_open_long = self.get_max_long() >= 100
        enough_time_has_passed = self.market.time - self.last_long_time > 0.25 if self.last_long_time >=0 else False
        if can_open_long:
            action_list.append(["open_long", 100])
            self.last_long_time = self.market.time
        elif has_opened_long and enough_time_has_passed:
            action_list.append(["close_long", 100, self.last_long_time])
            self.last_long_time = -1
        return action_list