"""
Implements abstract classes that control user behavior

TODO: rewrite all functions to have typed inputs
"""


from elfpy.utils.parse_json import parse_trade


class User:
    """
    Implements abstract classes that control user behavior
    user has a budget that is a dict, keyed with a date
    value is an inte with how many tokens they have for that date
    """

    def __init__(self, policy, rng, verbose=False):
        """
        Set up initial conditions
        """
        self.rng = rng
        self.verbose = verbose
        self.type = policy["type"]
        self.initial_budget = policy["budget"]
        self.trade_policy = policy["trade"]
        self.wallet = {
            "base": self.initial_budget
        }

    def get_trade(self, market):
        """Helper function for computing a user trade"""
        trade_action = parse_trade(self.trade_policy, market, self.rng)
        return trade_action

    def update_wallet(self, delta_wallet):
        """Update the user's wallet"""
        for key in delta_wallet:
            if key in self.wallet:
                self.wallet[key] += delta_wallet[key]
            else:
                self.wallet[key] = delta_wallet[key]
