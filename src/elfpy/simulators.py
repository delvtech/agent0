"""
Simulator class wraps the pricing models and markets
for experiment tracking and execution

TODO: rewrite all functions to have typed inputs
"""
from importlib import import_module
from elfpy.utils.fmt import *   # float→str formatter, also imports numpy as np
from elfpy.markets import Market
from elfpy.pricing_models import ElementPricingModel
from elfpy.pricing_models import HyperdrivePricingModel
from elfpy.utils.parse_config import parse_simulation_config
import elfpy.utils.time as time_utils
import elfpy.utils.price as price_utils


class YieldSimulator:
    """
    Stores environment variables & market simulation outputs for AMM experimentation

    Member variables include input settings, random variable ranges, and simulation outputs.
    To be used in conjunction with the Market and PricingModel classes
    """

    # TODO: set up member object that owns attributes instead of so many individual instance attributes
    # pylint: disable=too-many-instance-attributes

    def __init__(self, config_file):
        # pylint: disable=too-many-statements
        # User specified variables
        self.config = parse_simulation_config(config_file)
        self.reset_rng(np.random.default_rng(self.config.simulator.random_seed))
        # Simulation variables
        self.random_variables_set = False
        self.run_number = 0
        self.day = 0
        self.block_number = 0
        self.daily_block_number = 0
        seconds_in_a_day = 86400
        self.time_between_blocks = seconds_in_a_day / self.config.simulator.num_blocks_per_day
        self.run_trade_number = 0
        self.start_time = None
        self.init_share_price = None
        self.pricing_model = None
        self.market = None
        self.user_list = None
        self.random_variables_set = False
        # Output keys, used for logging on a trade-by-trade basis
        analysis_keys = [
            "run_number",  # integer, simulation index
            "simulation_start_time",  # start datetime for a given simulation
            "day",  # integer, day index in a given simulation
            "block_number",  # integer, block index in a given simulation
            "daily_block_number",  # integer, block index in a given day
            "block_timestamp",  # datetime of a given block's creation
            "current_market_datetime",  # float, current market time as a datetime
            "current_market_yearfrac",  # float, current market time as a yearfrac
            "run_trade_number",  # integer, trade number in a given simulation
            "step_size",
            "model_name",
            "token_duration",  # time lapse between token mint and expiry as a yearfrac
            "time_stretch_constant",
            "target_liquidity",
            "target_daily_volume",
            "pool_apy",
            "fee_percent",
            "floor_fee",  # minimum fee we take
            "init_vault_age",
            "base_asset_price",
            "vault_apy",
            "base_asset_reserves",
            "token_asset_reserves",
            "total_supply",
            "share_price",  # c in YieldSpace with Yield Bearing Vaults
            "init_share_price",  # u in YieldSpace with Yield Bearing Vaults
            "num_trading_days",  # number of days in a simulation
            "num_blocks_per_day",  # number of blocks in a day, simulates time between blocks
            "spot_price",
            "num_orders",
        ]
        self.analysis_dict = {key: [] for key in analysis_keys}

    def set_random_variables(self):
        """Use random number generator to assign initial simulation parameter values"""
        self.config.simulator.target_liquidity = self.rng.uniform(
            low=self.config.market.min_target_liquidity, high=self.config.market.max_target_liquidity
        )
        target_daily_volume_frac = self.rng.uniform(
            low=self.config.market.min_target_volume, high=self.config.market.max_target_volume
        )
        self.config.simulator.target_daily_volume = target_daily_volume_frac * self.config.simulator.target_liquidity
        self.config.simulator.init_pool_apy = self.rng.uniform(
            low=self.config.amm.min_pool_apy, high=self.config.amm.max_pool_apy
        )  # starting fixed apy as a decimal
        self.config.simulator.fee_percent = self.rng.uniform(self.config.amm.min_fee, self.config.amm.max_fee)
        # Determine real-world parameters for estimating initial (u) and current (c) price-per-share
        self.config.simulator.init_vault_age = self.rng.uniform(
            low=self.config.market.min_vault_age, high=self.config.market.max_vault_age
        )  # in years
        self.config.simulator.vault_apy = self.rng.uniform(
            low=self.config.market.min_vault_apy,
            high=self.config.market.max_vault_apy,
            size=self.config.simulator.num_trading_days,
        )  # vault apy over time as a decimal
        self.random_variables_set = True

    def print_random_variables(self):
        """Prints all variables that are set in set_random_variables()"""
        print(
            "Simulation random variables:\n"
            f"target_liquidity = {self.config.simulator.target_liquidity}\n"
            f"target_daily_volume = {self.config.simulator.target_daily_volume}\n"
            f"init_pool_apy = {self.config.simulator.init_pool_apy}\n"
            f"fee_percent = {self.config.simulator.fee_percent}\n"
            f"init_vault_age = {self.config.simulator.init_vault_age}\n"
            f"init_vault_apy = {self.config.simulator.vault_apy[0]}\n"
        )

    def get_simulation_state_string(self):
        """returns a formatted string containing all of the Simulation class member variables"""
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
        if self.config.simulator.verbose:
            print(f"{'#'*20} {model_name} {'#'*20}\n verbose=(simulator:{self.config.simulator.verbose},pricing_model:{self.config.pricing_model.verbose})")
        if model_name.lower() == "hyperdrive":
            self.pricing_model = HyperdrivePricingModel(self.config.pricing_model.verbose)
        elif model_name.lower() == "element":
            self.pricing_model = ElementPricingModel(self.config.pricing_model.verbose)
        else:
            raise ValueError(f'pricing_model_name must be "HyperDrive" or "Element", not {model_name}')

    def setup_simulated_entities(self, override_dict=None):
        """Constructs the user list, pricing model, and market member variables"""
        # update parameters if the user provided new ones
        assert (
            self.random_variables_set
        ), "ERROR: You must run simulator.set_random_variables() before constructing simulation entities"
        if override_dict is not None:
            for key, value in override_dict.items():
                for config_obj in [self.config.market, self.config.amm, self.config.simulator]:
                    if hasattr(config_obj, key):
                        setattr(config_obj, key, value)
                if key == "vault_apy":
                    if isinstance(value, float):
                        self.config.simulator.vault_apy = [value]*self.config.simulator.num_trading_days
                    else:
                        assert len(value) == self.config.simulator.num_trading_days, (
                            "vault_apy must have len equal to num_trading_days = "
                            + f"{self.config.simulator.num_trading_days},"
                            + f" not {len(value)}"
                        )
        if override_dict is not None and "init_share_price" in override_dict.keys():  # \mu variable
            self.init_share_price = override_dict["init_share_price"]
        else:
            self.init_share_price = (1 + self.config.simulator.vault_apy[0]) ** self.config.simulator.init_vault_age
            if self.config.simulator.precision is not None:
                self.init_share_price = np.around(self.init_share_price, self.config.simulator.precision)
        # setup pricing model
        self.set_pricing_model(self.config.simulator.pricing_model_name)  # construct pricing model object
        # setup market
        # TODO: redo this to initialize an empty market and add liquidity from an LP user
        time_stretch_constant = self.pricing_model.calc_time_stretch(self.config.simulator.init_pool_apy)
        # calculate x and y needed to deposit to hit target liquidity and APY
        init_reserves = price_utils.calc_liquidity(
            self.config.simulator.target_liquidity,
            self.config.market.base_asset_price,
            self.config.simulator.init_pool_apy,
            self.config.simulator.token_duration,
            time_stretch_constant,
            self.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            self.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
        )
        init_base_asset_reserves, init_token_asset_reserves = init_reserves[:2]
        self.market = Market(
            fee_percent=self.config.simulator.fee_percent,  # g
            token_duration=self.config.simulator.token_duration,
            pricing_model=self.pricing_model,
            time_stretch_constant=time_stretch_constant,
            init_share_price=self.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            share_price=self.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
            verbose=self.config.simulator.verbose,
        )
        if self.config.simulator.verbose:
            print(
                f"initial market values:"
                f"\n target_liquidity = {self.config.simulator.target_liquidity:,.0f}"
                f"\n init_base_asset_reserves = {init_base_asset_reserves:,.0f}"
                f"\n init_token_asset_reserves = {init_token_asset_reserves:,.0f}"
                f"\n fee_percent = {self.market.fee_percent}"
                f"\n share_price = {self.market.share_price}"
                f"\n init_share_price = {self.market.init_share_price}"
                f"\n init_time_stretch = {self.market.time_stretch_constant}"
            )
            print(f"{self.market.get_market_step_string()}")
        initial_lp = import_module(f"elfpy.strategies.init_LP").Policy(
            market=self.market,
            rng=self.rng,
            wallet_address=0,
            budget = init_base_asset_reserves*100,
            amount_to_LP = init_base_asset_reserves,
            pt_to_short = init_token_asset_reserves/10,
            short_until_apr = self.config.simulator.init_pool_apy,
            verbose=self.config.simulator.verbose
        )
        self.block_number = 0
        self.user_list = [initial_lp]
        # execute one special block just for the initial_lp
        self.collect_and_execute_trades()
        # continue adding other users
        for policy_number, policy_name in enumerate(self.config.simulator.user_policies):
            user_with_policy = import_module(f"elfpy.strategies.{policy_name}").Policy(
                market=self.market, rng=self.rng, wallet_address=policy_number+1,
            )
            if self.config.simulator.verbose:
                print(user_with_policy.status_report())
            self.user_list.append(user_with_policy)

    def step_size(self):
        """Returns minimum time increment"""
        blocks_per_year = 365 * self.config.simulator.num_blocks_per_day
        return 1 / blocks_per_year

    def run_simulation(self, override_dict=None):
        r"""
        Run the trade simulation and update the output state dictionary
        This is the primary function of the YieldSimulator class.
        The PricingModel and Market objects will be constructed.
        A loop will execute a group of trades with random volumes and directions for each day,
        up to `self.config.simulator.num_trading_days` days.

        Arguments
        ---------
        override_dict : dict
            Override member variables.
            Keys in this dictionary must match member variables of the YieldSimulator class.

        Returns
        -------
        There are no returns, but the function does update the analysis_dict member variable
        """
        self.start_time = time_utils.current_datetime()
        self.last_user_action_time = 0
        self.setup_simulated_entities(override_dict)
        last_block_in_sim = False
        for day in range(0, self.config.simulator.num_trading_days):
            self.day = day
            # Vault return can vary per day, which sets the current price per share
            if self.day > 0:  # Update only after first day (first day set to init_share_price)
                self.market.share_price += (
                    self.config.simulator.vault_apy[self.day]  # current day's apy
                    / 365  # convert annual yield to daily
                    * self.market.init_share_price  # APR, apply return to starting price (no compounding)
                    # * self.market.share_price # APY, apply return to latest price (full compounding)
                )
            for daily_block_number in range(self.config.simulator.num_blocks_per_day):
                if self.day == self.config.simulator.num_trading_days - 1:
                    if daily_block_number == self.config.simulator.num_blocks_per_day - 1:
                        last_block_in_sim = True
                self.daily_block_number = daily_block_number
                self.rng.shuffle(self.user_list)  # shuffle the user action order each block
                self.collect_and_execute_trades(last_block_in_sim)
                if not last_block_in_sim:
                    self.market.tick(self.step_size())
                    self.block_number += 1
        # simulation has ended
        for user in self.user_list:
            user.final_report()

    def collect_and_execute_trades(self, last_block_in_sim=False):
        for user in self.user_list:
            action_list = user.get_trade() if not last_block_in_sim else user.liquidate()
            for user_action in action_list:
                self.market.trade_and_update(user_action)
                self.update_analysis_dict()
                self.run_trade_number += 1
                self.last_user_action_time = self.market.time
                # TODO: convert to proper logging
        log_at_least_every_n_years = 0.1
        if (self.market.time - self.last_user_action_time > log_at_least_every_n_years/2) and (self.market.time - self.last_user_action_time) % log_at_least_every_n_years <= 1/365/self.config.simulator.num_blocks_per_day:
            print(f"{self.market.get_market_step_string()} 😴"\
                + f" {self.user_list[0].status_report()}"
            )

    def update_analysis_dict(self):
        """Increment the list for each key in the analysis_dict output variable"""
        # pylint: disable=too-many-statements
        # Variables that are constant across runs
        self.analysis_dict["model_name"].append(self.market.pricing_model.model_name())
        self.analysis_dict["run_number"].append(self.run_number)
        self.analysis_dict["time_stretch_constant"].append(self.market.time_stretch_constant)
        self.analysis_dict["target_liquidity"].append(self.config.simulator.target_liquidity)
        self.analysis_dict["target_daily_volume"].append(self.config.simulator.target_daily_volume)
        self.analysis_dict["fee_percent"].append(self.market.fee_percent)
        self.analysis_dict["floor_fee"].append(self.config.amm.floor_fee)
        self.analysis_dict["init_vault_age"].append(self.config.simulator.init_vault_age)
        self.analysis_dict["token_duration"].append(self.market.token_duration)
        self.analysis_dict["num_trading_days"].append(self.config.simulator.num_trading_days)
        self.analysis_dict["num_blocks_per_day"].append(self.config.simulator.num_blocks_per_day)
        self.analysis_dict["step_size"].append(self.step_size())
        self.analysis_dict["init_share_price"].append(self.market.init_share_price)
        self.analysis_dict["simulation_start_time"].append(self.start_time)
        # Variables that change per day
        self.analysis_dict["num_orders"].append(self.market.base_asset_orders + self.market.token_asset_orders)
        self.analysis_dict["vault_apy"].append(self.config.simulator.vault_apy[self.day])
        self.analysis_dict["day"].append(self.day)
        self.analysis_dict["daily_block_number"].append(self.daily_block_number)
        self.analysis_dict["block_number"].append(self.block_number)
        self.analysis_dict["block_timestamp"].append(
            time_utils.block_number_to_datetime(self.start_time, self.block_number, self.time_between_blocks)
        )
        # Variables that change per trade
        self.analysis_dict["current_market_yearfrac"].append(self.market.time)
        self.analysis_dict["current_market_datetime"].append(
            time_utils.yearfrac_as_datetime(self.start_time, self.market.time)
        )
        self.analysis_dict["run_trade_number"].append(self.run_trade_number)
        self.analysis_dict["base_asset_reserves"].append(self.market.share_reserves)
        self.analysis_dict["token_asset_reserves"].append(self.market.bond_reserves)
        self.analysis_dict["total_supply"].append(self.market.total_supply)
        self.analysis_dict["base_asset_price"].append(self.config.market.base_asset_price)
        self.analysis_dict["share_price"].append(self.market.share_price)
        self.analysis_dict["spot_price"].append(self.market.spot_price)
