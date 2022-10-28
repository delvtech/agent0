"""
Implements abstract classes that control user behavior

TODO: rewrite all functions to have typed inputs
"""

# Currently many functions use >5 arguments.
# These should be packaged up into shared variables, e.g.
#     reserves = (in_reserves, out_reserves)
#     share_prices = (init_share_price, share_price)
# pylint: disable=too-many-arguments

import numpy as np
from scipy.stats import binomtest

def build_user_list(config):
    """
    Collection of User objects
    config is a nested dictionary with the following structure
    config = {
        "rng" : # numpy.random.default_rng(seed) object
        "verbose" : # boolean
        "users" : user spec list
    config["users"] is a list of dictionaries containing user specifications
        each entry in the dictionary must contain "type" and "init_budget" keys
        each type will have additional required keys
    """
    user_spec_list = config["users"]
    user_list = []
    for user_spec in user_spec_list:
        user_type = user_spec["type"]
        if user_type == "random":
            user = RandomUser(config)
        elif user_type == "liquidity_provider":
            user = LiquidityProvider(config)
        user.set_budget(user_spec["init_budget"])
        user_list.append(user)
    return user_list


class User:
    """
    Implements abstract classes that control user behavior
    user has a budget that is a dict, keyed with a date
    value is an inte with how many tokens they have for that date
    """

    def __init__(self, **kwargs):
        """
        Set up initial conditions

        TODO: Like in simulators.py, we want to move away from kwargs for init config.
        """
        self.rng = kwargs["rng"]
        self.verbose = kwargs["verbose"]
        self.budget = None

    def set_budget(self, budget):
        self.budget = budget

    def get_direction_index(self):
        """Returns an index in the set (0, 1) that indicates the trade direction"""
        raise NotImplementedError

    def get_tokens_in_out(self, tokens):
        """Select one of two possible trade directions with some probability"""
        direction_index = self.get_direction_index()
        token_in = tokens[direction_index]
        token_out = tokens[1 - direction_index]
        return (token_in, token_out)

    def get_trade_amount_usd(self, target_reserves, target_volume, market_price):
        """
        Compute trade amount, which can't be more than the available reserves.

        TODO: Sync with smart contract team & parity their check for maximum trade amount
        """
        trade_mean = target_volume / 10
        trade_std = target_volume / 100
        trade_amount_usd = self.rng.normal(trade_mean, trade_std)
        trade_amount_usd = np.minimum(trade_amount_usd, target_reserves * market_price)
        return trade_amount_usd

    def get_trade(self, market, tokens, trade_direction, target_daily_volume, base_asset_price):
        """Helper function for computing a user trade"""
        (token_in, token_out) = self.get_tokens_in_out(tokens)
        target_reserves = market.get_target_reserves(token_in, trade_direction)
        trade_amount_usd = self.get_trade_amount_usd(
            target_reserves,
            target_daily_volume,
            base_asset_price,
        )
        return (token_in, token_out, trade_amount_usd)


class LiquidityProvider(User):
    """
    User that puts money into a pool and collects fees
    """
    pass # no extra ops for now


class RandomUser(User):
    def __init__(config):
        super().__init__(config)
        self.rng = config["rng"]

    def get_random_amount():
        return random.normal(100, 10)

class RandomHyperDriveUser(RandomUser):
    def get_random_action():
        return random("buy", "short", "sell")

class RandomV1User(RandomUser):
    """
    Random user that exercises fair behavior
    """
    def get_random_action():
        return random("buy", "sell")

    def get_action_plan():
        action_plan = []
        if market.apy > x:
            action = get_random_action
            amount = get_random_amount
            action_plan.append({action: amount})
        return action_plan
    
    def get_v1_actions():
        action_dict = []
        if market.apy > x:
            action = get_random_action
            amount = get_random_amount
            action_dict.append({action: amount})
        return action_dict

    def get_direction_index(self):
        """Select one of two possible trade directions with equal probability"""
        return self.rng.integers(low=0, high=2)  # 0 or 1


class WeightedRandomUser(RandomUser):
    """
    Implements abstract classes that control user behavior
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.days_trades = kwargs["days_trades"]
        self.pool_apy = kwargs["pool_apy"]
        self.pool_apy_target_range = kwargs["pool_apy_target_range"]
        self.pool_apy_target_range_convergence_speed = kwargs["pool_apy_target_range_convergence_speed"]
        state_keys = [
            "direction_index",
            "apy_distance_in_target_range",
            "apy_distance_from_mid_when_in_range",
            "actual_convergence_strength",
            "expected_proportion",
            "streak_luck",
            "btest",
        ]
        self.user_state = {key: [] for key in state_keys}

    def set_market_apy(self, apy):
        """Required to track simulation state variables"""
        self.pool_apy = apy

    def get_direction_index(self):
        """Select one of two possible trade directions with weighted probability"""
        return self.stochastic_direction(self.pool_apy)

    def stochastic_direction(self, pool_apy):
        """Picks p-value-weighted direction, cutting off tails"""
        # pylint: disable=too-many-arguments
        btest = []
        expected_proportion = 0
        streak_luck = 0
        apy_distance_in_target_range = np.clip(
            (pool_apy - self.pool_apy_target_range[0])
            / (self.pool_apy_target_range[1] - self.pool_apy_target_range[0]),
            0,
            1,
        )
        convergence_direction = (
            0 if apy_distance_in_target_range > 0.5 else 1
        )  # if you're above the midpoint of the targe range
        apy_distance_from_mid_when_in_range = np.clip(
            np.abs(apy_distance_in_target_range - 0.5) * 2, 0, 1
        )  # 0 if you're at the midpoint, 1 if you're at the edge
        actual_convergence_strength = (
            0.5 + (self.pool_apy_target_range_convergence_speed - 0.5) * apy_distance_from_mid_when_in_range
        )  # pool_apy_target_range_convergence_speed at edge or outside, scales to 0 at midpoint
        expected_proportion = (
            actual_convergence_strength if convergence_direction == 1 else 1 - actual_convergence_strength
        )
        if len(self.days_trades) > 0:
            btest = binomtest(
                k=sum(self.days_trades),
                n=len(self.days_trades),
                p=expected_proportion,
            )
            streak_luck = 1 - btest.pvalue
        if self.verbose and streak_luck > 0.98:
            direction_index = 1 - round(sum(self.days_trades) / len(self.days_trades))
            print(
                f" days_trades={self.days_trades}+{direction_index}k={sum(self.days_trades)}"
                f" n={len(self.days_trades)} ratio={sum(self.days_trades)/len(self.days_trades)}"
                f" streak_luck: {streak_luck}"
            )
        else:
            if 0 < apy_distance_from_mid_when_in_range < 1:
                actual_convergence_strength = (
                    actual_convergence_strength + (1 - actual_convergence_strength) * streak_luck**1.5
                )  # force convergence when on bad streaks
            direction_index = (
                convergence_direction if self.rng.random() < actual_convergence_strength else 1 - convergence_direction
            )
        self.days_trades.append(direction_index)
        if self.verbose and pool_apy > 0.2:
            print(
                f" days_trades={self.days_trades}"
                f" k={sum(self.days_trades)}"
                f" n={len(self.days_trades)}"
                f" ratio={sum(self.days_trades)/len(self.days_trades)}"
                f" streak_luck: {streak_luck}"
            )
            if self.pool_apy_target_range is not None:
                print(btest)
                print(f"expected_proportion={expected_proportion}")
                print(
                    f" pool_apy = {pool_apy:,.4%} apy_distance_in_target_range ="
                    f" {apy_distance_in_target_range},"
                    " apy_distance_from_mid_when_in_range ="
                    f" {apy_distance_from_mid_when_in_range},"
                    " actual_convergence_strength ="
                    f" {actual_convergence_strength}, direction_index ="
                    f" {direction_index}"
                )
        # Append new values the internal user state
        self.user_state["direction_index"].append(direction_index)
        self.user_state["apy_distance_from_mid_when_in_range"].append(apy_distance_from_mid_when_in_range)
        self.user_state["apy_distance_in_target_range"].append(apy_distance_in_target_range)
        self.user_state["actual_convergence_strength"].append(actual_convergence_strength)
        self.user_state["expected_proportion"].append(expected_proportion)
        self.user_state["streak_luck"].append(streak_luck)
        self.user_state["btest"].append(btest)
        return direction_index
