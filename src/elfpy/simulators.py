"""
Simulator class wraps the pricing models and markets
for experiment tracking and execution

TODO: rewrite all functions to have typed inputs
"""

import datetime
import pytz

from importlib import import_module

import numpy as np

from elfpy.markets import Market
from elfpy.pricing_models import ElementPricingModel
from elfpy.pricing_models import HyperdrivePricingModel


class YieldSimulator:
    """
    Stores environment variables & market simulation outputs for AMM experimentation

    Member variables include input settings, random variable ranges, and simulation outputs.
    To be used in conjunction with the Market and PricingModel classes
    """

    # TODO: set up member object that owns attributes instead of so many individual instance attributes
    # pylint: disable=too-many-instance-attributes

    def __init__(self, **kwargs):
        # TODO: Move away from using kwargs (this was a hack and can introduce bugs if the dict gets updated)
        #       Better to do named & typed args w/ defaults.
        #       This will also fix difficult-to-parse errors when variables are `None`.
        # TODO: change floor_fee to be a decimal like min_fee and max_fee
        # pylint: disable=too-many-statements

        # User specified variables
        self.min_fee = kwargs.get("min_fee")
        self.max_fee = kwargs.get("max_fee")
        self.floor_fee = kwargs.get("floor_fee")
        self.tokens = kwargs.get("tokens")  # tokens to be traded; list of strings
        self.min_target_liquidity = kwargs.get("min_target_liquidity")
        self.max_target_liquidity = kwargs.get("max_target_liquidity")
        self.min_target_volume = kwargs.get("min_target_volume")
        self.max_target_volume = kwargs.get("max_target_volume")
        self.min_pool_apy = kwargs.get("min_pool_apy")  # float (not a percentage)
        self.max_pool_apy = kwargs.get("max_pool_apy")  # float (not a percentage)
        self.pool_apy_target_range = kwargs.get("pool_apy_target_range")
        self.pool_apy_target_range_convergence_speed = kwargs.get("pool_apy_target_range_convergence_speed")
        self.streak_luck = kwargs.get("streak_luck")
        self.min_vault_age = kwargs.get("min_vault_age")
        self.max_vault_age = kwargs.get("max_vault_age")
        self.min_vault_apy = kwargs.get("min_vault_apy")  # float (not a percentage)
        self.max_vault_apy = kwargs.get("max_vault_apy")  # float (not a percentage)
        self.base_asset_price = kwargs.get("base_asset_price")
        self.precision = kwargs.get("precision")
        self.pricing_model_name = str(kwargs.get("pricing_model_name"))
        self.scenario_name = str(kwargs.get("scenario_name"))
        self.trade_direction = kwargs.get("trade_direction")
        self.token_duration = kwargs.get("token_duration")
        self.num_trading_days = kwargs.get("num_trading_days")
        self.num_blocks_per_day = kwargs.get("num_blocks_per_day")
        self.user_policies = kwargs.get("user_policies")
        self.rng = kwargs.get("rng")
        self.verbose = kwargs.get("verbose")
        # Random variables
        self.target_liquidity = None
        self.target_daily_volume = None
        self.init_pool_apy = None
        self.fee_percent = None
        self.init_vault_age = None
        self.vault_apy = None
        self.random_variables_set = False
        # Simulation variables
        self.run_number = 0 
        self.day = 0
        self.block_number = 0
        self.daily_block_number = 0
        self.run_trade_number = 0
        self.start_time = None
        self.expected_proportion = 0
        self.init_time_stretch = 1
        self.init_share_price = None
        self.time_stretch = None
        self.pricing_model = None
        self.market = None
        self.user_list = None
        self.trade_amount = None
        self.trade_amount_usd = None
        self.token_in = None
        self.token_out = None
        self.without_fee_or_slippage = None
        self.with_fee = None
        self.without_fee = None
        self.fee = None
        self.random_variables_set = False
        self.apy_distance_in_target_range = None
        self.apy_distance_from_mid_when_in_range = None
        self.actual_convergence_strength = None
        # Output keys, used for logging on a trade-by-trade basis
        analysis_keys = [
            "run_number",# integer, simulation index
            "simulation_start_time", # start datetime for a given simulation
            "day", # integer, day index in a given simulation
            "block_number", # integer, block index in a given simulation
            "block_timestamp", # datetime of a given block's creation
            "run_trade_number", # integer, trade number in a given simulation
            "model_name",
            "scenario_name",
            "token_duration", # time lapse between token mint and expiry
            "init_time_stretch",
            "target_liquidity",
            "target_daily_volume",
            "pool_apy",
            "pool_apy_target_range",
            "pool_apy_target_range_convergence_speed",
            "streak_luck",
            "fee_percent",
            "floor_fee", # minimum fee we take
            "init_vault_age",
            "base_asset_price",
            "vault_apy",
            "base_asset_reserves",
            "token_asset_reserves",
            "total_supply",
            "token_in",
            "token_out",
            "trade_direction",
            "trade_amount",
            "trade_amount_usd",
            "share_price",  # c in YieldSpace with Yield Bearing Vaults
            "init_share_price",  # u in YieldSpace with Yield Bearing Vaults
            "out_without_fee_slippage",
            "out_with_fee",
            "out_without_fee",
            "apy_distance_in_target_range",
            "apy_distance_from_mid_when_in_range",
            "actual_convergence_strength",
            "fee", # percentage of the slippage we take as a fee (expressed as a decimal)
            "slippage",
            "num_trading_days", # number of days in a simulation
            "num_blocks_per_day", # number of blocks in a day, simulates time between blocks
            "spot_price",
            "num_orders",
        ]
        self.analysis_dict = {key: [] for key in analysis_keys}

    def set_random_variables(self):
        """Use random number generator to assign initial simulation parameter values"""
        self.target_liquidity = self.rng.uniform(self.min_target_liquidity, self.max_target_liquidity)
        target_daily_volume_frac = self.rng.uniform(self.min_target_volume, self.max_target_volume)
        self.target_daily_volume = target_daily_volume_frac * self.target_liquidity
        self.init_pool_apy = self.rng.uniform(self.min_pool_apy, self.max_pool_apy)  # starting fixed apy as a decimal
        self.fee_percent = self.rng.uniform(self.min_fee, self.max_fee)
        # Determine real-world parameters for estimating initial (u) and current (c) price-per-share
        self.init_vault_age = self.rng.uniform(self.min_vault_age, self.max_vault_age)  # in years
        self.vault_apy = self.rng.uniform(
            self.min_vault_apy, self.max_vault_apy, size=self.num_trading_days
        )  # vault apy over time as a decimal
        self.random_variables_set = True

    def print_random_variables(self):
        """Prints all variables that are set in set_random_variables()"""
        print(
            "Simulation random variables:\n"
            + f"target_liquidity = {self.target_liquidity}\n"
            + f"target_daily_volume = {self.target_daily_volume}\n"
            + f"init_pool_apy = {self.init_pool_apy}\n"
            + f"fee_percent = {self.fee_percent}\n"
            + f"init_vault_age = {self.init_vault_age}\n"
            + f"init_vault_apy = {self.vault_apy[0]}\n"
        )

    def get_simulation_state_string(self):
        """Returns a formatted string containing all of the Simulation class member variables"""
        strings = []
        for attribute, value in self.__dict__.items():
            if attribute not in ("analysis_dict", "rng"):
                strings.append(f"{attribute} = {value}")
        state_string = "\n".join(strings)
        return state_string

    def reset_rng(self, rng):
        """
        Assign the internal random number generator to a new instantiation

        This function is useful for forcing identical trade volume and directions across simulation runs
        """

        assert isinstance(
            rng, type(np.random.default_rng())
        ), f"rng type must be a random number generator, not {type(rng)}."
        self.rng = rng

    def set_pricing_model(self, model_name):
        """Assign a PricingModel object to the pricing_model attribute"""
        if model_name.lower() == "hyperdrive":
            self.pricing_model = HyperdrivePricingModel(self.verbose)
        elif model_name.lower() == "element":
            self.pricing_model = ElementPricingModel(self.verbose)
        else:
            raise ValueError(f'pricing_model_name must be "HyperDrive" or "Element", not {model_name}')

    def setup_simulated_entities(self, override_dict=None):
        """Constructs the user list, pricing model, and market member variables"""
        # update parameters if the user provided new ones
        assert (
            self.random_variables_set
        ), "ERROR: You must run simulator.set_random_variables() before running the simulation"
        if override_dict is not None:
            for key in override_dict.keys():
                if hasattr(self, key):
                    setattr(self, key, override_dict[key])
                    if key == "vault_apy":
                        assert len(override_dict[key]) == self.num_trading_days, (
                            f"vault_apy must have len equal to num_trading_days = {self.num_trading_days},"
                            + f" not {len(override_dict[key])}"
                        )
        if override_dict is not None and "init_share_price" in override_dict.keys():  # \mu variable
            self.init_share_price = override_dict["init_share_price"]
        else:
            self.init_share_price = (1 + self.vault_apy[0]) ** self.init_vault_age
            if self.precision is not None:
                self.init_share_price = np.around(self.init_share_price, self.precision)
        # setup pricing model
        self.set_pricing_model(self.pricing_model_name) # construct pricing model object
        self.init_time_stretch = self.pricing_model.calc_time_stretch(self.init_pool_apy)
        # setup market
        init_reserves = self.pricing_model.calc_liquidity(
            self.target_liquidity,
            self.base_asset_price,
            self.init_pool_apy,
            self.token_duration,
            self.init_time_stretch,
            self.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            self.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
        )
        init_base_asset_reserves, init_token_asset_reserves = init_reserves[:2]
        self.market = Market(
            base_asset=init_base_asset_reserves, # x
            token_asset=init_token_asset_reserves, # y
            fee_percent=self.fee_percent, # g
            pricing_model=self.pricing_model,
            init_share_price=self.init_share_price, # u from YieldSpace w/ Yield Baring Vaults
            share_price=self.init_share_price, # c from YieldSpace w/ Yield Baring Vaults
            verbose=self.verbose,
        )
        # setup user list
        self.user_list = []
        for policy_name in self.user_policies:
            user_with_policy = import_module(f"elfpy.strategies.{policy_name}")\
                .Policy(self.market, self.rng, self.verbose)
            self.user_list.append(user_with_policy)

    def step_size(self):
        """Returns minimum time increment"""
        blocks_per_year = 365 * self.num_blocks_per_day
        return 1 / blocks_per_year

    def block_number_to_timestamp(self, block_number):
        """Converts the current block number to a datetime based on the start datetime of the simulation"""
        seconds_in_a_day = 86400
        time_between_blocks = seconds_in_a_day / self.num_blocks_per_day
        delta_time = datetime.timedelta(seconds=block_number * time_between_blocks)
        return self.start_time + delta_time

    @staticmethod
    def current_time():
        """Returns the current time"""
        return datetime.datetime.now(pytz.timezone('Etc/GMT-0'))

    def get_time_remaining(self, mint_time=None):
        """Get the time remaining on a token"""
        time_elapsed = (self.current_time() - mint_time).total_seconds()
        total_time = datetime.timedelta(days=self.token_duration).total_seconds()
        time_remaining = 1 - (time_elapsed / total_time)
        return time_remaining

    def get_yearfrac_remaining(self, mint_time=None):
        """Get the year fraction remaining on a token"""
        if mint_time is None or mint_time == -1:
            mint_time = self.market.time
        yearfrac_elapsed = self.market.time - mint_time
        yearfrac_token_duration = self.token_duration/365
        time_remaining = yearfrac_token_duration - yearfrac_elapsed
        return time_remaining

    def compute_time_delta(year_fraction_time):
        """TODO"""
        return 0

    def market_time_to_wall_time(self):
        """TODO"""
        time_delta = self.compute_time_delta(self.market.time)
        return self.start_time + time_delta

    def run_simulation(self, override_dict=None):
        """
        Run the trade simulation and update the output state dictionary

        Arguments:
        override_dict [dict] Override member variables.
        Keys in this dictionary must match member variables of the YieldSimulator class.

        This is the primary function of the YieldSimulator class.
        The PricingModel and Market objects will be constructed.
        A loop will execute a group of trades with random volumes and directions for each day,
        up to `self.num_trading_days` days.
        """

        self.start_time = self.current_time()
        self.block_number = 0
        self.setup_simulated_entities(override_dict)
        for day in range(0, self.num_trading_days):
            self.day = day
            # Vault return can vary per day, which sets the current price per share
            if self.day > 0:  # Update only after first day (first day set to init_share_price)
                self.market.share_price += (
                    self.vault_apy[self.day] # current day's apy
                    / 365 # convert annual yield to daily
                    * self.market.init_share_price # APR, apply return to starting price (no compounding)
                    # * self.market.share_price # APY, apply return to latest price (full compounding)
                )
            for daily_block_number in range(self.num_blocks_per_day):
                self.daily_block_number = daily_block_number
                self.rng.shuffle(self.user_list) # shuffle the user action order each block
                for user in self.user_list:
                    trade_list = user.get_trade()
                    if len(trade_list) == 0: # empty list indicates no action
                        pass
                    for trade in trade_list:
                        print(trade)
                        self.token_in, self.trade_direction, self.trade_amount_usd, self.mint_time = (
                            trade["token_in"],
                            trade["direction"],
                            trade["trade_amount"],
                            trade["mint_time"],
                        )
                        self.trade_amount = self.trade_amount_usd / self.base_asset_price  # convert to token units
                        # Conduct trade & update state
                        time_remaining = self.get_yearfrac_remaining(self.mint_time)
                        user_state_update = self.market.swap(
                            self.trade_amount,  # in units of target asset
                            self.trade_direction, # in vs out
                            self.token_in,  # base or pt
                            time_remaining
                        )
                        # Update user state
                        user.update_wallet(user_state_update)
                        self.update_analysis_dict()
                        self.run_trade_number += 1
                        if self.verbose:
                            print(
                                "YieldSimulator.run_simulation:\n"
                                + f"trades={self.market.base_asset_orders + self.market.token_asset_orders} "
                                + f"init_share_price={self.market.init_share_price}, "
                                + f"share_price={self.market.share_price}, "
                                + f"amount={self.trade_amount}, "
                                + f"reserves={(self.market.base_asset, self.market.token_asset)}"
                            )
                self.market.tick(self.step_size())
                self.block_number += 1
        self.run_number += 1

    def update_analysis_dict(self):
        """Increment the list for each key in the analysis_dict output variable"""
        # pylint: disable=too-many-statements
        # Variables that are constant across runs
        self.analysis_dict["model_name"].append(self.market.pricing_model.model_name())
        self.analysis_dict["scenario_name"].append(self.scenario_name)
        self.analysis_dict["run_number"].append(self.run_number)
        self.analysis_dict["init_time_stretch"].append(self.init_time_stretch)
        self.analysis_dict["target_liquidity"].append(self.target_liquidity)
        self.analysis_dict["target_daily_volume"].append(self.target_daily_volume)
        self.analysis_dict["pool_apy_target_range"].append(self.pool_apy_target_range)
        self.analysis_dict["pool_apy_target_range_convergence_speed"].append(
            self.pool_apy_target_range_convergence_speed
        )
        self.analysis_dict["streak_luck"].append(self.streak_luck)
        self.analysis_dict["fee_percent"].append(self.market.fee_percent)
        self.analysis_dict["floor_fee"].append(self.floor_fee)
        self.analysis_dict["init_vault_age"].append(self.init_vault_age)
        self.analysis_dict["token_duration"].append(self.token_duration)
        self.analysis_dict["num_trading_days"].append(self.num_trading_days)
        self.analysis_dict["num_blocks_per_day"].append(self.num_blocks_per_day)
        #self.analysis_dict["step_size"].append(self.step_size)
        self.analysis_dict["init_share_price"].append(self.market.init_share_price)
        self.analysis_dict["simulation_start_time"].append(self.start_time)
        # Variables that change per day
        self.analysis_dict["num_orders"].append(self.market.base_asset_orders + self.market.token_asset_orders)
        self.analysis_dict["vault_apy"].append(self.vault_apy[self.day])
        self.analysis_dict["day"].append(self.day)
        self.analysis_dict["daily_block_number"].append(self.daily_block_number)
        self.analysis_dict["block_number"].append(self.block_number)
        self.analysis_dict["block_timestamp"].append(self.block_number_to_timestamp(self.block_number))
        # Variables that change per trade
        self.analysis_dict["run_trade_number"].append(self.run_trade_number)
        self.analysis_dict["base_asset_reserves"].append(self.market.base_asset)
        self.analysis_dict["token_asset_reserves"].append(self.market.token_asset)
        self.analysis_dict["total_supply"].append(self.market.total_supply)
        self.analysis_dict["base_asset_price"].append(self.base_asset_price)
        self.analysis_dict["token_in"].append(self.token_in)
        self.analysis_dict["token_out"].append(self.token_out)
        self.analysis_dict["trade_direction"].append(self.trade_direction)
        self.analysis_dict["trade_amount"].append(self.trade_amount)
        self.analysis_dict["trade_amount_usd"].append(self.trade_amount_usd)
        self.analysis_dict["share_price"].append(self.market.share_price)
        self.analysis_dict["apy_distance_in_target_range"].append(self.apy_distance_in_target_range)
        self.analysis_dict["apy_distance_from_mid_when_in_range"].append(self.apy_distance_from_mid_when_in_range)
        self.analysis_dict["actual_convergence_strength"].append(self.actual_convergence_strength)
        if self.fee is None:
            self.analysis_dict["out_without_fee_slippage"].append(None)
            self.analysis_dict["out_with_fee"].append(None)
            self.analysis_dict["out_without_fee"].append(None)
            self.analysis_dict["fee"].append(None)
            self.analysis_dict["slippage"].append(None)
        else:
            self.analysis_dict["out_without_fee_slippage"].append(self.without_fee_or_slippage * self.base_asset_price)
            self.analysis_dict["out_with_fee"].append(self.with_fee * self.base_asset_price)
            self.analysis_dict["out_without_fee"].append(self.without_fee * self.base_asset_price)
            self.analysis_dict["fee"].append(self.fee * self.base_asset_price)
            slippage = (self.without_fee_or_slippage - self.without_fee) * self.base_asset_price
            self.analysis_dict["slippage"].append(slippage)
        self.analysis_dict["spot_price"].append(self.market.spot_price())
