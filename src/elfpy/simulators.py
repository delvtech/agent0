"""
Simulator class wraps the pricing models and markets
for experiment tracking and execution

TODO: rewrite all functions to have typed inputs
"""

from __future__ import annotations
import datetime
import json
import logging
from typing import Optional

import numpy as np
from numpy.random._generator import Generator

from elfpy.agent import Agent
from elfpy.markets import Market
from elfpy.pricing_models.base import PricingModel
from elfpy.utils.config import Config
from elfpy.utils import sim_utils  # utilities for setting up a simulation
import elfpy.utils.time as time_utils
from elfpy.utils.outputs import CustomEncoder


class Simulator:
    """
    Stores environment variables & market simulation outputs for AMM experimentation

    Member variables include input settings, random variable ranges, and simulation outputs.
    To be used in conjunction with the Market and PricingModel classes
    """

    # TODO: set up member (dataclass?) object that owns attributes instead of so many individual instance attributes
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        config: Config,
        pricing_model: PricingModel,
        market: Market,
        agents: dict[int, Agent],
        rng: Generator,
        random_simulation_variables: Optional[list] = None,
    ):
        # pylint: disable=too-many-arguments
        # pylint: disable=too-many-statements
        # User specified variables
        self.config = config
        self.log_config_variables()
        self.pricing_model = pricing_model
        self.market = market
        self.agents = agents
        self.set_rng(rng)
        if random_simulation_variables is None:
            self.random_variables = sim_utils.get_random_variables(self.config, self.rng)
        else:
            self.random_variables = random_simulation_variables
        self.check_vault_apy_type()
        # Simulation variables
        self.run_number = 0
        self.day = 0
        self.block_number = 0
        self.daily_block_number = 0
        seconds_in_a_day = 86400
        self.time_between_blocks = seconds_in_a_day / self.config.simulator.num_blocks_per_day
        self.run_trade_number = 0
        self.start_time: datetime.datetime | None = None
        # Output keys, used for logging on a trade-by-trade basis
        analysis_keys = [
            "model_name",  # the name of the pricing model that is used in simulation
            "run_number",  # integer, simulation index
            "simulation_start_time",  # start datetime for a given simulation
            "day",  # integer, day index in a given simulation
            "block_number",  # integer, block index in a given simulation
            "daily_block_number",  # integer, block index in a given day
            "block_timestamp",  # datetime of a given block's creation
            "current_market_datetime",  # float, current market time as a datetime
            "current_market_yearfrac",  # float, current market time as a yearfrac
            "run_trade_number",  # integer, trade number in a given simulation
            "market_step_size",  # minimum time discretization for market time step
            "position_duration",  # time lapse between token mint and expiry as a yearfrac
            "target_liquidity",
            "fee_percent",
            "floor_fee",  # minimum fee we take
            "init_vault_age",
            "base_asset_price",
            "vault_apy",
            "pool_apy",
            "share_reserves",  # from market state
            "bond_reserves",  # from market state
            "base_buffer",  # from market state
            "bond_buffer",  # from market state
            "lp_reserves",  # from market state
            "share_price",  # from market state
            "init_share_price",  # from market state
            "num_trading_days",  # number of days in a simulation
            "num_blocks_per_day",  # number of blocks in a day, simulates time between blocks
            "spot_price",
        ]
        self.analysis_dict = {key: [] for key in analysis_keys}

    def check_vault_apy_type(self) -> None:
        """Recast the vault apy into a list of floats if a float was given on init"""
        if isinstance(self.random_variables.vault_apy, float):
            self.random_variables.vault_apy = [
                float(self.random_variables.vault_apy)
            ] * self.config.simulator.num_trading_days
        else:  # check that the length is correct
            if not len(self.random_variables.vault_apy) == self.config.simulator.num_trading_days:
                raise ValueError(
                    "vault_apy must have len equal to num_trading_days = "
                    + f"{self.config.simulator.num_trading_days},"
                    + f" not {len(self.random_variables.vault_apy)}"
                )

    def set_rng(self, rng: Generator) -> None:
        """Assign the internal random number generator to a new instantiation
        This function is useful for forcing identical trade volume and directions across simulation runs

        Arguments
        ---------
        rng : Generator
            Random number generator, constructed using np.random.default_rng(seed)
        """
        if not isinstance(rng, Generator):
            raise TypeError(f"rng type must be a random number generator, not {type(rng)}.")
        self.rng = rng

    def log_config_variables(self) -> None:
        """Prints all variables that are in config"""
        # cls arg tells json how to handle numpy objects and nested dataclasses
        config_string = json.dumps(self.config.__dict__, sort_keys=True, indent=2, cls=CustomEncoder)
        logging.info(config_string)

    def get_simulation_state_string(self) -> str:
        """Returns a formatted string containing all of the Simulation class member variables

        Returns
        ---------
        state_string : str
            Simulator class member variables (keys & values in self.__dict__) cast to a string, separated by a new line
        """
        strings = []
        for attribute, value in self.__dict__.items():
            if attribute not in ("analysis_dict", "rng"):
                strings.append(f"{attribute} = {value}")
        state_string = "\n".join(strings)
        return state_string

    def market_step_size(self) -> float:
        """Returns minimum time increment

        Returns
        ---------
        float
            time between blocks, which is computed as 1 / blocks_per_year
        """
        blocks_per_year = 365 * self.config.simulator.num_blocks_per_day
        return 1 / blocks_per_year

    def override_variables(self, override_dict):
        """Replace existing member & config variables with ones defined in override_dict"""
        # override the config variables, including random variables that were set
        for key, value in override_dict.items():
            for config_obj in [self.config.market, self.config.amm, self.config.simulator]:
                if hasattr(config_obj, key):  # TODO: This is not safe -- we should assign each key individually
                    setattr(config_obj, key, value)
                    if key == "vault_apy":  # support for float or list[float] types
                        if isinstance(value, float):  # overwrite above setattr with the value replicated in a list
                            self.config.simulator.vault_apy = [float(value)] * self.config.simulator.num_trading_days
                        else:  # check that the length is correct; if so, then it is already set above
                            assert len(value) == self.config.simulator.num_trading_days, (
                                "vault_apy must have len equal to num_trading_days = "
                                + f"{self.config.simulator.num_trading_days},"
                                + f" not {len(value)}"
                            )
            if hasattr(self, key):
                logging.info("Overriding %s from %s to %s.", key, str(getattr(self, key)), str(value))
            else:
                logging.info("Overriding %s from %s to %s.", key, "None", str(value))
        # override the init_share_price if it is in the override_dict
        if "init_share_price" in override_dict.keys():
            self.init_share_price = override_dict["init_share_price"]  # \mu variable

    def setup_init_lp_agent(self):
        """
        Calculate the required deposit amounts and instantiate the LP agent

        Arguments
        ---------
        last_block_in_sim : bool
            If True, indicates if the current set of trades are occuring on the final block in the simulation
        """
        # get the reserve amounts for the target liquidity and pool APR
        init_share_reserves, init_bond_reserves = price_utils.calc_liquidity(
            target_liquidity=self.config.simulator.target_liquidity,
            market_price=self.config.market.base_asset_price,
            apr=self.config.simulator.init_pool_apy,
            days_remaining=self.config.simulator.token_duration,
            time_stretch=self.market.time_stretch_constant,
            init_share_price=self.market.init_share_price,
            share_price=self.market.init_share_price,
        )[:2]
        normalized_days_until_maturity = self.config.simulator.token_duration  # `t(d)`; full duration
        stretch_time_remaining = time_utils.stretch_time(
            normalized_days_until_maturity, self.market.time_stretch_constant
        )  # tau(d)
        # mock the short to assess what the delta market conditions will be
        output_with_fee = self.market.pricing_model.calc_out_given_in(
            in_=init_bond_reserves,
            share_reserves=init_share_reserves,
            bond_reserves=0,
            token_out="pt",
            fee_percent=self.config.simulator.fee_percent,
            time_remaining=stretch_time_remaining,
            init_share_price=self.market.init_share_price,
            share_price=self.market.init_share_price,
        )[1]
        # output_with_fee will be subtracted from the share reserves, so we want to add that much extra in
        base_to_lp = init_share_reserves + output_with_fee
        # budget is the full amount for LP & short
        budget = base_to_lp + init_bond_reserves
        # construct the init_lp agent with desired budget, lp, and short amounts
        init_lp_agent = import_module("elfpy.strategies.init_lp").Policy(
            market=self.market,
            rng=self.rng,
            wallet_address=0,
            budget=budget,
            base_to_lp=base_to_lp,
            pt_to_short=init_bond_reserves,
        )
        logging.info(
            (
                "Init LP agent #%03.0f statistics:\ntarget_apy = %g; target_liquidity = %g; "
                "budget = %g; base_to_lp = %g; pt_to_short = %g"
            ),
            init_lp_agent.wallet_address,
            self.config.simulator.init_pool_apy,
            self.config.simulator.target_liquidity,
            budget,
            base_to_lp,
            init_bond_reserves,
        )
        return init_lp_agent

    def validate_custom_parameters(self, policy_instruction):
        """
        separate the policy name from the policy arguments and validate the arguments
        """
        policy_name, policy_args = policy_instruction.split(":")
        try:
            policy_args = policy_args.split(",")
        except AttributeError as exception:
            logging.info("ERROR: No policy arguments provided")
            raise exception
        try:
            policy_args = [arg.split("=") for arg in policy_args]
        except AttributeError as exception:
            logging.info("ERROR: Policy arguments must be provided as key=value pairs")
            raise exception
        try:
            kwargs = {key: float(value) for key, value in policy_args}
        except ValueError as exception:
            logging.info("ERROR: Policy arguments must be provided as key=value pairs")
            raise exception
        return policy_name, kwargs

    def setup_simulated_entities(self, override_dict=None):
        """
        Constructs the agent list, pricing model, and market member variables

        Arguments
        ---------
        override_dict : dict
            Override member variables.
            Keys in this dictionary must match member variables of the YieldSimulator class.

        Returns
        -------
        There are no returns, but the function instantiates self.market and self.agents
        """

        assert (
            self.random_variables_set
        ), "ERROR: You must run simulator.set_random_variables() before constructing simulation entities"
        if override_dict is not None:
            self.override_variables(override_dict)  # apply the override dict
        pricing_model = self._get_pricing_model(self.config.amm.pricing_model_name)  # construct pricing model object
        # setup market
        time_stretch_constant = pricing_model.calc_time_stretch(self.config.simulator.init_pool_apy)
        self.market = Market(
            fee_percent=self.config.simulator.fee_percent,  # g
            token_duration=self.config.simulator.token_duration,
            pricing_model=pricing_model,
            time_stretch_constant=time_stretch_constant,
            init_share_price=self.init_share_price,  # u from YieldSpace w/ Yield Baring Vaults
            share_price=self.init_share_price,  # c from YieldSpace w/ Yield Baring Vaults
        )
        self.market.vault_apy = self.config.simulator.vault_apy[0]
        # fill market pools
        if self.config.simulator.init_lp:
            init_lp_agent = self.setup_init_lp_agent()  # calculate lp amounts & instantiate lp agent
            self.agents = {init_lp_agent.wallet_address: init_lp_agent}
            # execute one special block just for the init_lp_agent
            self.collect_and_execute_trades()
        else:  # manual market configuration
            self.agents = {}
        self.market.log_market_step_string()
        # continue adding other users
        for policy_number, policy_instruction in enumerate(self.config.simulator.user_policies):
            if ":" in policy_instruction:  # we have custom parameters
                policy_name, kwargs = self.validate_custom_parameters(policy_instruction)
            else:  # we don't havev custom parameters
                policy_name = policy_instruction
                kwargs = {}
            logging.info(
                "creating agent #%03.0f with policy %s and args %s",
                policy_number + 1,
                policy_name,
                kwargs,
            )
            agent = import_module(f"elfpy.strategies.{policy_name}").Policy(
                market=self.market,
                rng=self.rng,
                wallet_address=policy_number + 1,  # reserve agent 000 for init_lp, even if not used
                **kwargs,
            )
            agent.log_status_report()
            self.agents.update({agent.wallet_address: agent})

    def run_simulation(self) -> None:
        r"""
        Run the trade simulation and update the output state dictionary
        This is the primary function of the Simulator class.
        The PricingModel and Market objects will be constructed.
        A loop will execute a group of trades with random volumes and directions for each day,
        up to `self.config.simulator.num_trading_days` days.

        Returns
        -------
        There are no returns, but the function does update the analysis_dict member variable
        """
        if not isinstance(self.market, Market):
            raise ValueError("Market not defined")
        last_block_in_sim = False
        self.start_time = time_utils.current_datetime()
        for day in range(0, self.config.simulator.num_trading_days):
            self.day = day
            # Vault return can vary per day, which sets the current price per share
            if self.day > 0:  # Update only after first day (first day set to init_share_price)
                self.market.market_state.share_price += (
                    self.random_variables.vault_apy[self.day]  # current day's apy
                    / 365  # convert annual yield to daily
                    * self.market.market_state.init_share_price  # APR, apply return to starting price (no compounding)
                    # * self.market.share_price # APY, apply return to latest price (full compounding)
                )
            for daily_block_number in range(self.config.simulator.num_blocks_per_day):
                self.daily_block_number = daily_block_number
                last_block_in_sim = (self.day == self.config.simulator.num_trading_days - 1) and (
                    self.daily_block_number == self.config.simulator.num_blocks_per_day - 1
                )
                self.collect_and_execute_trades(last_block_in_sim)
                logging.debug("day = %d, daily_block_number = %d\n", self.day, self.daily_block_number)
                self.market.log_market_step_string(self.pricing_model)
                if not last_block_in_sim:
                    self.market.tick(self.market_step_size())
                    self.block_number += 1
        # simulation has ended
        for agent in self.agents.values():
            agent.log_final_report(self.market, self.pricing_model)

    def collect_and_execute_trades(self, last_block_in_sim=False):
        """Get trades from the agent list, execute them, and update states"""
        if not isinstance(self.market, Market):
            raise ValueError("market not defined")
        number_of_executed_trades = 0
        # TODO: This is a HACK to prevent the initial LPer from rugging other agents.
        # The initial LPer should be able to remove their liquidity and any open shorts can still be closed.
        # But right now, if the LPer removes liquidity while shorts are open,
        # then closing the shorts results in an error (share_reserves == 0).
        if self.config.simulator.shuffle_users:
            if last_block_in_sim:
                wallet_ids = self.rng.permutation(  # shuffle wallets except init_lp
                    [key for key in self.agents if key > 0]  # exclude init_lp before shuffling
                )
                wallet_ids = np.append(wallet_ids, 0)  # add init_lp so that they're always last
            else:  # include init_lp only on the last block, to let it unwind
                wallet_ids = self.rng.permutation(list(self.agents))
        else:  # we are in a deterministic mode
            # reverse the list excluding 0 (init_lp)
            wallet_ids = [key for key in self.agents if key > 0][::-1]
            if self.config.simulator.init_lp and last_block_in_sim:  # prepend init_lp to the list
                wallet_ids = np.append(wallet_ids, 0)
        for agent_id in wallet_ids:  # trade is different on the last block
            agent = self.agents[agent_id]
            if last_block_in_sim:  # get all of a agent's trades
                trade_list = agent.get_liquidation_trades()
            else:
                trade_list = agent.get_trade_list()
            for agent_trade in trade_list:  # execute trades
                wallet_deltas = self.market.trade_and_update(agent_trade)
                agent.update_wallet(wallet_deltas)  # update agent state since market doesn't know about agents
                logging.debug(
                    "agent #%03.0f wallet deltas = \n%s",
                    agent.wallet_address,
                    wallet_deltas.__dict__,
                )
                agent.log_status_report()
                self.update_analysis_dict()
                self.run_trade_number += 1
                number_of_executed_trades += 1
        if number_of_executed_trades > 0:
            logging.info("executed %f trades at %s", number_of_executed_trades, self.market.get_market_state_string())

    def update_analysis_dict(self):
        """Increment the list for each key in the analysis_dict output variable"""
        # pylint: disable=too-many-statements

        if not isinstance(self.market, Market):
            raise ValueError("Market not defined")
        self.analysis_dict["model_name"].append(self.pricing_model.model_name())
        self.analysis_dict["run_number"].append(self.run_number)
        self.analysis_dict["simulation_start_time"].append(self.start_time)
        self.analysis_dict["day"].append(self.day)
        self.analysis_dict["block_number"].append(self.block_number)
        self.analysis_dict["daily_block_number"].append(self.daily_block_number)
        self.analysis_dict["block_timestamp"].append(
            time_utils.block_number_to_datetime(self.start_time, self.block_number, self.time_between_blocks)
            if self.start_time
            else "None"
        )
        self.analysis_dict["current_market_datetime"].append(
            time_utils.yearfrac_as_datetime(self.start_time, self.market.time) if self.start_time else "None"
        )
        self.analysis_dict["current_market_yearfrac"].append(self.market.time)
        self.analysis_dict["run_trade_number"].append(self.run_trade_number)
        self.analysis_dict["market_step_size"].append(self.market_step_size())
        self.analysis_dict["position_duration"].append(self.market.position_duration)
        self.analysis_dict["target_liquidity"].append(self.random_variables.target_liquidity)
        self.analysis_dict["fee_percent"].append(self.market.fee_percent)
        self.analysis_dict["floor_fee"].append(self.config.amm.floor_fee)
        self.analysis_dict["init_vault_age"].append(self.random_variables.init_vault_age)
        self.analysis_dict["base_asset_price"].append(self.config.market.base_asset_price)
        self.analysis_dict["vault_apy"].append(self.random_variables.vault_apy[self.day])
        self.analysis_dict["pool_apy"].append(self.market.get_rate(self.pricing_model))
        for key, val in self.market.market_state.__dict__.items():
            self.analysis_dict[key].append(val)
        self.analysis_dict["num_trading_days"].append(self.config.simulator.num_trading_days)
        self.analysis_dict["num_blocks_per_day"].append(self.config.simulator.num_blocks_per_day)
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        if self.market.market_state.share_reserves > 0:  # there is money in the market
            self.analysis_dict["spot_price"].append(self.market.get_spot_price(self.pricing_model))
        else:
            self.analysis_dict["spot_price"].append(np.nan)
