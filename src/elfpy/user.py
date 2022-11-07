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
        self.type = policy["type"]
        self.initial_budget = policy["budget"]
        self.trade_policy = policy["trade"]
        self.wallet = {
            "base": self.initial_budget
        }
        self.rng = rng
        self.verbose = verbose

    def get_max_long(self):
        """what is the amount of base that the user can spend"""
        return self.wallet["base"]

    def get_max_short(self, market):
        """
        what is the amount of PTs to short that has a max loss of my current base balance
        """
        max_short = market.policy.calc_max_pts_to_short(self.wallet["base"])
        return max_short

    def get_trade(self, market):
        """Helper function for computing a user trade"""
        trade_action = parse_trade(self.trade_policy, market, self.rng)
        if trade_action is not None:
            token_in, token_out, trade_amount_usd = trade_action
            assert trade_amount_usd >= 0, (
                f"user.py: ERROR: Trade amount should not be negative, but is {trade_amount_usd}"
                f" token_in={token_in} token_out={token_out}"
            )
        return trade_action

    def update_wallet(self, delta_wallet):
        """Update the user's wallet"""
        for key in delta_wallet:
            if key in self.wallet:
                self.wallet[key] += delta_wallet[key]
            else:
                self.wallet[key] = delta_wallet[key]
