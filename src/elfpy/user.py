"""
Implements abstract classes that control user behavior

TODO: rewrite all functions to have typed inputs
"""


from dataclasses import dataclass
from dataclasses import field


import numpy as np


import elfpy.utils.time as time_utils
from elfpy.utils.bcolors import bcolors


class User:
    """
    Implements abstract classes that control user behavior
    user has a budget that is a dict, keyed with a date
    value is an inte with how many tokens they have for that date
    """

    def __init__(self, market, rng, wallet_address, budget=0, verbose=False):
        """
        Set up initial conditions
        """
        self.market = market
        self.budget = budget
        assert self.budget >= 0, f"ERROR: budget should be initialized (>=0), but is {self.budget}"
        self.wallet = self.UserWallet(base_in_wallet=self.budget)
        self.rng = rng
        self.wallet_address = wallet_address
        self.verbose = verbose
        self.last_update_spend = 0
        self.product_of_time_and_base = 0
        self.weighted_average_spend = 0
        self.position_list = []

    @dataclass
    class UserWallet:
        """user wallet store"""

        base_in_wallet: float = 0
        lp_in_wallet: float = 0  # they're fungible!
        token_in_wallet: dict = field(default_factory=dict)
        base_in_protocol: dict = field(default_factory=dict)
        token_in_protocol: dict = field(default_factory=dict)

        def __getitem__(self, key):
            return getattr(self, key)

        def __setitem__(self, key, value):
            setattr(self, key, value)

        def update(self, *args, **kwargs):
            return self.__dict__.update(*args, **kwargs)

        def keys(self):
            return self.__dict__.keys()

        def values(self):
            return self.__dict__.values()

        def items(self):
            return self.__dict__.items()

    @dataclass
    class UserAction:
        """user action specification"""

        action_type: str
        trade_amount: float
        mint_time: float = None
        market: object = None
        fee_percent: float = field(init=False)
        init_share_price: float = field(init=False)
        share_price: float = field(init=False)  
        share_reserves: float = field(init=False)
        bond_reserves: float = field(init=False)
        share_buffer: float = field(init=False)
        bond_buffer: float = field(init=False)
        liquidity_pool: float = field(init=False)
        rate: float = field(init=False)
        time_remaining: float = field(init=False)
        stretched_time_remaining: float = field(init=False)
        wallet_address: int = field(init=False)

        def set_variables(self, market, wallet_address):
            self.market = market
            if self.mint_time is None:
                self.mint_time = self.market.time
            self.fee_percent = self.market.fee_percent
            self.init_share_price = self.market.init_share_price
            self.share_price = self.market.share_price
            self.share_reserves = self.market.share_reserves
            self.bond_reserves = self.market.bond_reserves
            self.share_buffer = self.market.share_buffer
            self.bond_buffer = self.market.bond_buffer
            self.liquidity_pool = self.market.liquidity_pool
            self.rate = self.market.rate
            self.wallet_address = wallet_address
            self.time_remaining = time_utils.get_yearfrac_remaining(
                self.market.time, self.mint_time, self.market.token_duration
            )
            self.stretched_time_remaining = time_utils.stretch_time(
                self.time_remaining, self.market.time_stretch_constant
            )

    def create_user_action(self, action_type, trade_amount):
        user_action = self.UserAction(action_type, trade_amount)
        user_action.set_variables(self.market, self.wallet_address)
        return user_action

    def action(self):
        """Specify action from the policy"""
        raise NotImplementedError

    def get_max_long(self):
        """Returns the amount of base that the user can spend."""
        return np.minimum(self.wallet.base_in_wallet, self.market.bond_reserves)

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
            self.wallet.base_in_wallet,
            self.market.share_reserves,
            self.market.bond_reserves,
            "base",
            self.market.fee_percent,
            stretched_time_remaining,
            self.market.init_share_price,
            self.market.share_price,
        )[1]
        max_short = self.wallet.base_in_wallet + output_with_fee - eps
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
        for action in action_list:  # edit each action in place
            if action.mint_time is None:
                action.mint_time = self.market.time
            if action.action_type == "close_short":
                action.token_in_protocol = self.wallet.token_in_protocol[action.mint_time]
                action.base_in_protocol = self.wallet.base_in_protocol[action.mint_time]
            if action.action_type == "close_short":
                action.token_in_protocol = self.wallet.token_in_protocol[action.mint_time]
                action.base_in_protocol = self.wallet.base_in_protocol[action.mint_time]
        # TODO: Add safety checks
        # e.g. if trade amount > 0, whether there is enough money in the account
        # if len(trade_action) > 0: # there is a trade
        #    token_in, token_out, trade_amount_usd = trade_action
        #    assert trade_amount_usd >= 0, (
        #        f"user.py: ERROR: Trade amount should not be negative, but is {trade_amount_usd}"
        #        f" token_in={token_in} token_out={token_out}"
        #    )
        return action_list

    def update_spend(self):
        print(f"  time={self.market.time} last_update_spend={self.last_update_spend} budget={self.budget} base_in_wallet={self.wallet['base_in_wallet']}") if self.verbose else None
        new_spend = (self.market.time - self.last_update_spend) * (self.budget - self.wallet["base_in_wallet"])
        self.product_of_time_and_base += new_spend
        self.weighted_average_spend = self.product_of_time_and_base / self.market.time if self.market.time > 0 else 0
        print(f"  weighted_average_spend={self.weighted_average_spend} added {new_spend} deltaT={self.market.time - self.last_update_spend} delta₡={self.budget - self.wallet['base_in_wallet']}") if self.verbose else None
        self.last_update_spend = self.market.time
        return self.weighted_average_spend

    def update_wallet(self, trade_result):
        """Update the user's wallet"""
        self.update_spend()
        for key, value in trade_result.items():
            if value is None:
                pass
            elif key in ["base_in_wallet", "lp_in_wallet"]:
                    self.wallet[key] += value
            elif key in ["base_in_protocol", "token_in_wallet", "token_in_protocol"]:
                mint_time = value[0]
                delta_token = value[1]
                if mint_time in self.wallet[key]:
                    self.wallet[key][mint_time] += delta_token
                elif key == "fee":
                    pass
                else:
                    self.wallet[key].update({mint_time: delta_token})
            elif key == "fee":
                pass
            else:
                raise ValueError(f"key={key} is not allowed.")
        # TODO: convert to proper logging
        # TODO: This verbose section upsets the linter bc it creates too many branches
        if self.verbose:
            wallet_string = ""
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

    def final_report(self):
        price = self.market.spot_price
        base = self.wallet['base_in_wallet']
        tokens = sum(self.position_list)
        worth = base + tokens * price
        PnL = worth - self.budget
        spend = self.weighted_average_spend
        holding_period_rate = PnL / spend if spend != 0 else 0
        annual_percentage_rate = holding_period_rate / self.market.time
        print(
            f" 🤖 {bcolors.FAIL}{self.wallet_address}{bcolors.ENDC}"\
            + f" net worth = ₡{bcolors.FAIL}{worth}{bcolors.ENDC}"\
            + f" from {base} base and {tokens} tokens at p={price}\n"
            + f"  made {holding_period_rate:,.2%} in {self.market.time*365:,.2f} days"
            + f" over {self.market.time} years that\'s an APR of {bcolors.OKGREEN}"
            + f"{annual_percentage_rate:,.2%}{bcolors.ENDC} on ₡{spend} weighted average spend"
        )