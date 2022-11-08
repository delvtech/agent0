"""
Implements abstract classes that control user behavior

TODO: rewrite all functions to have typed inputs
"""


# from elfpy.utils.parse_json import parse_trade


class User:
    """
    Implements abstract classes that control user behavior
    user has a budget that is a dict, keyed with a date
    value is an inte with how many tokens they have for that date
    """

    def __init__(self, market, rng, verbose=False, budget=1000):
        """
        Set up initial conditions
        """
        self.market = market
        self.budget = budget
        assert self.budget >= 0, f"ERROR: budget should be initialized (>=0), but is {self.budget}"
        self.wallet = {
            "base": self.budget
        }
        self.rng = rng
        self.verbose = verbose

    def action(self):
        """Specify action from the policy"""
        raise NotImplementedError

    def get_max_long(self):
        """Returns the amount of base that the user can spend."""
        return self.wallet["base"]

    def get_max_short(self, market):
        """
        what is the amount of PTs to short that has a max loss of my current base balance
        """
        max_short = self.wallet["base"]
        PTsold = market.pricing_model.calcInGivenOut(max_short)
        discount = max_short - PTsold
        while discount < self.wallet["base"]:
            max_short += 1
            PTsold = market.pricing_model.calcInGivenOut(max_short)
            discount = max_short - PTsold
        return max_short - 1 # subtract 1 to get the max short

    def get_trade(self):
        """
        Helper function for computing a user trade
        direction is chosen based on this logic:
        when entering a trade (open long or short),
        we use calcOutGivenIn because we know how much we want to spend,
        and care less about how much we get for it.
        when exiting a trade (close long or short),
        we use calcInGivenOut because we know how much we want to get,
        and care less about how much we have to spend.
        we spend what we have to spend, and get what we get.
        """
        # trade_action = parse_trade(self.policy, market, self.rng)
        trade_action = self.action() # get the action list from the policy
        print(f"trade_action: {trade_action}")
        trade_details = []
        for trade in trade_action:
            if trade[0] == "open_long": # buy to open long
                trade_detail = {
                    "trade_amount": trade[1],
                    "direction": "out",  # calcOutGivenIn
                    "token_in": "base"   # buy unknown PT with known base
                }
            elif trade[0] == "close_long": # sell to close long
                trade_detail = {
                    "trade_amount": trade[1],
                    "direction": "out",  # calcOutGivenIn
                    "token_in": "pt"     # sell back known PT for unknown base
                }
            elif trade[0] == "open_short": # sell to open short
                trade_detail = {
                    "trade_amount": trade[1],
                    "direction": "out", # calcOutGivenIn
                    "token_in": "pt"    # sell known PT for unknown base
                }
            elif trade[0] == "close_short": # buy to close short
                trade_detail = {
                    "trade_amount": trade[1],
                    "direction": "in",  # calcInGivenOut
                    "token_in": "base"  # buy back known PT for unknown base
                }
            else:
                raise ValueError(f"ERROR: unknown trade type {trade[0]}")
            trade_details.append(trade_detail)

        # TODO: checks that e.g. trade amount > 0; there is enough money in the account
        #if len(trade_action) > 0: # there is a trade
        #    token_in, token_out, trade_amount_usd = trade_action
        #    assert trade_amount_usd >= 0, (
        #        f"user.py: ERROR: Trade amount should not be negative, but is {trade_amount_usd}"
        #        f" token_in={token_in} token_out={token_out}"
        #    )

        # return the formatted action set to be passed to the market
        return trade_action

    def update_wallet(self, delta_wallet):
        """Update the user's wallet"""
        for key in delta_wallet:
            if key in self.wallet:
                self.wallet[key] += delta_wallet[key]
            else:
                self.wallet[key] = delta_wallet[key]
