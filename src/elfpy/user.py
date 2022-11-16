"""
Implements abstract classes that control user behavior

TODO: rewrite all functions to have typed inputs
"""


import numpy as np


import elfpy.utils.time as time_utils
from elfpy.utils.bcolors import bcolors

# from elfpy.utils.parse_json import parse_trade
class User:
    """
    Implements abstract classes that control user behavior
    user has a budget that is a dict, keyed with a date
    value is an inte with how many tokens they have for that date
    """

    def __init__(self, market, rng, budget=0, verbose=False):
        """
        Set up initial conditions
        """
        self.market = market
        self.budget = budget
        assert self.budget >= 0, f"ERROR: budget should be initialized (>=0), but is {self.budget}"
        self.wallet = {
            "base_in_wallet": self.budget,
            "base_in_protocol": {},
            "token_in_wallet": {},
            "token_in_protocol": {},
        }
        self.rng = rng
        self.verbose = verbose
        self.last_update_spend = 0
        self.weighted_average_spend = 0

    def action(self):
        """Specify action from the policy"""
        raise NotImplementedError

    def get_max_long(self):
        """Returns the amount of base that the user can spend."""
        return np.minimum(self.wallet["base_in_wallet"], self.market.bond_reserves)

    def get_max_short(self, mint_time, eps=1.0):
        """
        Returns an approximation of maximum amount of base that the user can short given current market conditions

        TODO: This currently is a first-order approximation.
        An alternative is to do this iteratively and find a max trade, but that is probably too slow.
        Maybe we could add an optional flag to iteratively solve it, like num_iters.
        """
        time_remaining = time_utils.get_yearfrac_remaining(self.market.time, mint_time, self.market.token_duration)
        stretched_time_remaining = time_utils.stretch_time(time_remaining, self.market.time_stretch_constant)
        output_with_fee = self.market.pricing_model.calc_out_given_in(
            self.wallet["base_in_wallet"],
            self.market.share_reserves,
            self.market.bond_reserves,
            "base",
            self.market.fee_percent,
            stretched_time_remaining,
            self.market.init_share_price,
            self.market.share_price,
        )[1]
        max_short = self.wallet["base_in_wallet"] + output_with_fee - eps
        return max_short

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
        action_list = self.action()  # get the action list from the policy
        action_list_dict = []
        for action in action_list:
            action_dict = {}
            action_dict["action_type"] = action[0]
            action_dict["trade_amount"] = action[1]
            if len(action) > 2:  # close, so mint_time is the time for the token we want to close
                action_dict["mint_time"] = action[2]
            else:  # open, so mint_time is assigned to current market time (fresh mint)
                action_dict["mint_time"] = self.market.time
            if action_dict["action_type"] == "close_short":
                action_dict["token_in_protocol"] = self.wallet["token_in_protocol"][action_dict["mint_time"]]
                action_dict["base_in_protocol"] = self.wallet["base_in_protocol"][action_dict["mint_time"]]
            action_list_dict.append(action_dict)
        # TODO: Add safety checks
        # e.g. if trade amount > 0, whether there is enough money in the account
        # if len(trade_action) > 0: # there is a trade
        #    token_in, token_out, trade_amount_usd = trade_action
        #    assert trade_amount_usd >= 0, (
        #        f"user.py: ERROR: Trade amount should not be negative, but is {trade_amount_usd}"
        #        f" token_in={token_in} token_out={token_out}"
        #    )
        return action_list_dict

    def update_spend(self):
        print(f"  time={self.market.time} last_update_spend={self.last_update_spend} budget={self.budget} base_in_wallet={self.wallet['base_in_wallet']}")
        new_spend = (self.market.time - self.last_update_spend) * (self.budget - self.wallet["base_in_wallet"])
        self.weighted_average_spend += new_spend
        print(f"  weighted_average_spend={self.weighted_average_spend} added {new_spend} deltaT={self.market.time - self.last_update_spend} delta₡={self.budget - self.wallet['base_in_wallet']}")
        self.last_update_spend = self.market.time
        return self.weighted_average_spend

    def update_wallet(self, trade_result):
        """Update the user's wallet"""
        for key, value in trade_result.items():
            if value is not None:
                if key == "base_in_wallet":
                    self.update_spend()
                    self.wallet[key] += value
                elif key in ["base_in_protocol", "token_in_wallet", "token_in_protocol"]:
                    mint_time = value[0]
                    delta_token = value[1]
                    if mint_time in self.wallet[key]:
                        self.wallet[key][mint_time] += delta_token
                    else:
                        self.wallet[key].update({mint_time: delta_token})
                elif key == "fee":
                    pass
                else:
                    raise ValueError(f"key={key} is not allowed.")
        wallet_string = ""
        # for account_dict in self.wallet.values():
        #     for mint_time, amount in account_dict.items():
        #         wallet_string += f"{mint_time}: {amount} "
        for key, value in self.wallet.items():
            if isinstance(value, dict):
                total_amount = sum(value.values())
                if total_amount != 0:
                    color = bcolors.OKGREEN if sum(value.values()) > 0 else bcolors.WARNING
                    wallet_string += f" {key} = ₡{color}{sum(value.values())}{bcolors.ENDC}"
            elif isinstance(value, (int, float)):
                if value != 0:
                    color = bcolors.OKGREEN if value > 0 else bcolors.WARNING
                    wallet_string += f" {key} = ₡{color}{value}{bcolors.ENDC}"
        # wallet_string = ", ".join([f"{key}=₡{sum(value.values()):,.2f}" for key, value in self.wallet.items()])
        print(f" hello, human. this 🤖 now has{wallet_string} of your puny currencies")