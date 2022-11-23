"""
Simulator class wraps the pricing models and markets
for experiment tracking and execution

TODO: rewrite all functions to have typed inputs
"""


from importlib import import_module


import numpy as np


from elfpy.markets import Market
from elfpy.pricing_models import ElementPricingModel
from elfpy.pricing_models import HyperdrivePricingModel
from elfpy.utils.parse_config import parse_simulation_config
import elfpy.utils.time as time_utils
from elfpy.utils.bcolors import bcolors
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
        self.target_liquidity = self.rng.uniform(
            low=self.config.market.min_target_liquidity, high=self.config.market.max_target_liquidity
        )
        target_daily_volume_frac = self.rng.uniform(
            low=self.config.market.min_target_volume, high=self.config.market.max_target_volume
        )
        self.target_daily_volume = target_daily_volume_frac * self.target_liquidity
        self.init_pool_apy = self.rng.uniform(
            low=self.config.amm.min_pool_apy, high=self.config.amm.max_pool_apy
        )  # starting fixed apy as a decimal
        self.fee_percent = self.rng.uniform(self.config.amm.min_fee, self.config.amm.max_fee)
        # Determine real-world parameters for estimating initial (u) and current (c) price-per-share
        self.init_vault_age = self.rng.uniform(
            low=self.config.market.min_vault_age, high=self.config.market.max_vault_age
        )  # in years
        self.vault_apy = self.rng.uniform(
            low=self.config.market.min_vault_apy,
            high=self.config.market.max_vault_apy,
            size=self.config.simulator.num_trading_days,
        )  # vault apy over time as a decimal
        self.random_variables_set = True

    def print_random_variables(self):
        """Prints all variables that are set in set_random_variables()"""
        print(
            "Simulation random variables:\n"
            f"target_liquidity = {self.target_liquidity}\n"
            f"target_daily_volume = {self.target_daily_volume}\n"
            f"init_pool_apy = {self.init_pool_apy}\n"
            f"fee_percent = {self.fee_percent}\n"
            f"init_vault_age = {self.init_vault_age}\n"
            f"init_vault_apy = {self.vault_apy[0]}\n"
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
        print("\n\n", model_name, "\n\n")
        if model_name.lower() == "hyperdrive":
            self.pricing_model = HyperdrivePricingModel(self.config.simulator.verbose)
        elif model_name.lower() == "element":
            self.pricing_model = ElementPricingModel(self.config.simulator.verbose)
        else:
            raise ValueError(f'pricing_model_name must be "HyperDrive" or "Element", not {model_name}')

    def setup_simulated_entities(self, override_dict=None):
        """Constructs the user list, pricing model, and market member variables"""
        # update parameters if the user provided new ones
        assert (
            self.random_variables_set
        ), "ERROR: You must run simulator.set_random_variables() before constructing simulation entities"
        if override_dict is not None:
            for key in override_dict.keys():
                for config_obj in [self.config.market, self.config.amm, self.config.simulator]:
                    if hasattr(config_obj, key):
                        setattr(config_obj, key, override_dict[key])
                        if key == "vault_apy":
                            assert len(override_dict[key]) == self.config.simulator.num_trading_days, (
                                "vault_apy must have len equal to num_trading_days = "
                                + f"{self.config.simulator.num_trading_days},"
                                + f" not {len(override_dict[key])}"
                            )
        if override_dict is not None and "init_share_price" in override_dict.keys():  # \mu variable
            self.init_share_price = override_dict["init_share_price"]
        else:
            self.init_share_price = (1 + self.vault_apy[0]) ** self.init_vault_age
            if self.config.simulator.precision is not None:
                self.init_share_price = np.around(self.init_share_price, self.config.simulator.precision)
        # setup pricing model
        self.set_pricing_model(self.config.simulator.pricing_model_name)  # construct pricing model object
        # setup market
        # TODO: redo this to initialize an empty market and add liquidity from an LP user
        time_stretch_constant = self.pricing_model.calc_time_stretch(self.init_pool_apy)
        init_reserves = price_utils.calc_liquidity(
            self.target_liquidity,
            self.config.market.base_asset_price,
            self.init_pool_apy,
            self.config.simulator.token_duration,
            time_stretch_constant,
            self.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            self.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
        )
        init_base_asset_reserves, init_token_asset_reserves = init_reserves[:2]
        self.market = Market(
            share_reserves=init_base_asset_reserves,  # z
            bond_reserves=init_token_asset_reserves,  # y
            fee_percent=self.fee_percent,  # g
            token_duration=self.config.simulator.token_duration,
            pricing_model=self.pricing_model,
            time_stretch_constant=time_stretch_constant,
            init_share_price=self.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            share_price=self.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
            verbose=self.config.simulator.verbose,
        )
        if self.config.simulator.verbose:
            print(
                f"\n-----\ninitial market values:"
                f"\nshare_reserves = {self.market.share_reserves}"
                f"\nbond_reserves = {self.market.bond_reserves}"
                f"\ntarget_liquidity = {self.target_liquidity}"
                f"\ntotal market liquidity = {self.market.share_reserves + self.market.bond_reserves}"
                f"\nfee_percent = {self.market.fee_percent}"
                f"\nshare_price = {self.market.share_price}"
                f"\ninit_share_price = {self.market.init_share_price}"
                f"\ninit_time_stretch = {self.market.time_stretch_constant}"
                "\n-----\n"
            )
        # setup user list
        self.user_list = []
        for policy_name in self.config.simulator.user_policies:
            user_with_policy = import_module(f"elfpy.strategies.{policy_name}").Policy(
                market=self.market, rng=self.rng, verbose=self.config.simulator.verbose
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
        self.block_number = 0
        self.setup_simulated_entities(override_dict)
        for day in range(0, self.config.simulator.num_trading_days):
            self.day = day
            # Vault return can vary per day, which sets the current price per share
            if self.day > 0:  # Update only after first day (first day set to init_share_price)
                self.market.share_price += (
                    self.vault_apy[self.day]  # current day's apy
                    / 365  # convert annual yield to daily
                    * self.market.init_share_price  # APR, apply return to starting price (no compounding)
                    # * self.market.share_price # APY, apply return to latest price (full compounding)
                )
            for daily_block_number in range(self.config.simulator.num_blocks_per_day):
                self.daily_block_number = daily_block_number
                self.rng.shuffle(self.user_list)  # shuffle the user action order each block
                for user in self.user_list:
                    action_list = user.get_trade()
                    if len(action_list) == 0:  # empty list indicates no action
                        pass
                    for user_action in action_list:
                        # Conduct trade & update state
                        user_action.time_remaining = time_utils.get_yearfrac_remaining(
                            self.market.time, user_action.mint_time, self.market.token_duration
                        )
                        user_action.stretched_time_remaining = time_utils.stretch_time(
                            user_action.time_remaining, self.market.time_stretch_constant
                        )
                        action_result = self.market.swap(user_action)
                        if self.config.simulator.verbose:
                            print(
                                f"t={bcolors.HEADER}{self.market.time}{bcolors.ENDC}"
                                f" reserves=[x={bcolors.OKBLUE}{self.market.share_reserves}{bcolors.ENDC}"
                                f",y={bcolors.OKBLUE}{self.market.bond_reserves}{bcolors.ENDC}]\n"
                                f" action: {user_action}\n result: {action_result}"
                            )
                        # Update user state
                        user.update_wallet(action_result)
                        self.update_analysis_dict()
                        self.run_trade_number += 1
                # TODO: convert to proper logging; @wakamex fix variable names
                if self.config.simulator.verbose:
                    # TODO: convert "last_user_action_time" to proper logging
                    # (used for debug only, not part of simulation output)
                    last_user_action_time = self.analysis_dict["current_market_yearfrac"][self.run_trade_number - 1]
                    # print(
                    #     "YieldSimulator.run_simulation:"
                    #     f"\n\ttime = {self.market.time}"
                    #     f"\n\tuser trade = {user_action}"
                    #     f"\n\tuser_wallet = {user.wallet}"
                    #     f"\n\tinit pool apy = {self.init_pool_apy}"
                    #     f"\n\ttrades = {self.market.base_asset_orders + self.market.token_asset_orders}"
                    #     f"\n\tinit_share_price = {self.market.init_share_price}"
                    #     f"\n\tshare_price = {self.market.share_price}"
                    #     f"\n\treserves = {(self.market.share_reserves, self.market.bond_reserves)}"
                    # )
                    if (self.market.time - last_user_action_time > 0.1) and (
                        self.market.time - last_user_action_time
                    ) % 0.5 < 1 / 365 / self.config.simulator.num_blocks_per_day / 2:
                        print(
                            f"t={bcolors.HEADER}{self.market.time}{bcolors.ENDC}"
                            + f" reserves=[x={bcolors.OKBLUE}{self.market.share_reserves}{bcolors.ENDC}"
                            + f",y={bcolors.OKBLUE}{self.market.bond_reserves}{bcolors.ENDC}]\n"
                            + " no user action 😴"
                            + f" user report = {self.user_list[0].status_report()}"
                        )
                    if (
                        day == self.config.simulator.num_trading_days - 1
                        and daily_block_number == self.config.simulator.num_blocks_per_day - 1
                    ):
                        user = self.user_list[0]
                        worth = user.wallet.base_in_wallet + sum(user.position_list) / self.market.spot_price
                        annual_percentage_rate = (
                            (worth - user.budget) / (user.update_spend() / self.market.time)
                        ) / self.market.time
                        print(
                            f"SIM_END t={bcolors.HEADER}{self.market.time}{bcolors.ENDC}"
                            f" reserves=[x={bcolors.OKBLUE}{self.market.share_reserves}{bcolors.ENDC}"
                            f", y={bcolors.OKBLUE}{self.market.bond_reserves}{bcolors.ENDC}]\n"
                            f" user result 😱 = ₡{bcolors.FAIL}{worth}{bcolors.ENDC} from"
                            f" {user.wallet.base_in_wallet} base and {sum(user.position_list)}"
                            f" tokens at p={1 / self.market.spot_price}\n over {self.market.time}"
                            f" years that's an APR of {bcolors.OKGREEN}{annual_percentage_rate:,.2%}{bcolors.ENDC} on"
                            f" ₡{(user.update_spend() / self.market.time)} weighted average spend"
                        )
                self.market.tick(self.step_size())
                self.block_number += 1
        self.run_number += 1

    def update_analysis_dict(self):
        """Increment the list for each key in the analysis_dict output variable"""
        # pylint: disable=too-many-statements
        # Variables that are constant across runs
        self.analysis_dict["model_name"].append(self.market.pricing_model.model_name())
        self.analysis_dict["run_number"].append(self.run_number)
        self.analysis_dict["time_stretch_constant"].append(self.market.time_stretch_constant)
        self.analysis_dict["target_liquidity"].append(self.target_liquidity)
        self.analysis_dict["target_daily_volume"].append(self.target_daily_volume)
        self.analysis_dict["fee_percent"].append(self.market.fee_percent)
        self.analysis_dict["floor_fee"].append(self.config.amm.floor_fee)
        self.analysis_dict["init_vault_age"].append(self.init_vault_age)
        self.analysis_dict["token_duration"].append(self.market.token_duration)
        self.analysis_dict["num_trading_days"].append(self.config.simulator.num_trading_days)
        self.analysis_dict["num_blocks_per_day"].append(self.config.simulator.num_blocks_per_day)
        self.analysis_dict["step_size"].append(self.step_size())
        self.analysis_dict["init_share_price"].append(self.market.init_share_price)
        self.analysis_dict["simulation_start_time"].append(self.start_time)
        # Variables that change per day
        self.analysis_dict["num_orders"].append(self.market.base_asset_orders + self.market.token_asset_orders)
        self.analysis_dict["vault_apy"].append(self.vault_apy[self.day])
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
