"""Simulator class wraps the pricing models and markets for experiment tracking and execution"""

from __future__ import annotations  # types will be strings by default in 3.11
from typing import Optional, TYPE_CHECKING
import datetime
import json
import logging

import numpy as np
from numpy.random._generator import Generator

from elfpy.utils import sim_utils  # utilities for setting up a simulation
import elfpy.utils.time as time_utils
from elfpy.utils.outputs import CustomEncoder
from elfpy.types import MarketDeltas, SimulationState

if TYPE_CHECKING:
    from elfpy.agent import Agent
    from elfpy.markets import Market
    from elfpy.pricing_models.base import PricingModel
    from elfpy.utils.config import Config


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
        random_simulation_variables: Optional[sim_utils.RandomSimulationVariables] = None,
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
        self.check_vault_apr_type()
        # Simulation variables
        self.run_number = 0
        self.day = 0
        self.block_number = 0
        self.daily_block_number = 0
        seconds_in_a_day = 86400
        self.time_between_blocks = seconds_in_a_day / self.config.simulator.num_blocks_per_day
        self.run_trade_number = 0
        self.start_time: datetime.datetime | None = None
        self.simulation_state = SimulationState()

    def check_vault_apr_type(self) -> None:
        """Recast the vault apy into a list of floats if a float was given on init"""
        if isinstance(self.random_variables.vault_apr, float):
            self.random_variables.vault_apr = [
                float(self.random_variables.vault_apr)
            ] * self.config.simulator.num_trading_days
        else:  # check that the length is correct
            if not len(self.random_variables.vault_apr) == self.config.simulator.num_trading_days:
                raise ValueError(
                    "vault_apr must have len equal to num_trading_days = "
                    + f"{self.config.simulator.num_trading_days},"
                    + f" not {len(self.random_variables.vault_apr)}"
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
            if attribute not in ("simulation_state", "rng"):
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

    def add_agents(self, agent_list: list[Agent]) -> None:
        """Append the agents and simulation_state member variables

        If trades have already happened (as indicated by self.run_trade_number), then empty wallet states are
        prepended to the simulation_state for each new agent so that the state can still easily be converted into
        a pandas dataframe.

        Arguments
        ---------
        agent_list : list[Agent]
            A list of instantiated Agent objects
        """
        for agent in agent_list:
            # add the agent to the agents list
            self.agents.update({agent.wallet.address: agent})
            # update the simulator state to include null wallet for each prior trade
            state_vector_length = len(agent.wallet.state) + 1
            agent_state = []
            for trade_number in range(self.run_trade_number):
                agent_state.append([trade_number] + [None] * state_vector_length)
            setattr(self.simulation_state, f"agent_{agent.wallet.address}", agent_state)

    def collect_and_execute_trades(self, last_block_in_sim: bool = False) -> None:
        """Get trades from the agent list, execute them, and update states

        Arguments
        ---------
        last_block_in_sim : bool
            If True, indicates if the current set of trades are occuring on the final block in the simulation
        """
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
            else:
                wallet_ids = self.rng.permutation(
                    list(self.agents)
                )  # random permutation of keys (agent wallet addresses)
        for agent_id in wallet_ids:  # trade is different on the last block
            agent = self.agents[agent_id]
            if last_block_in_sim:  # get all of a agent's trades
                trade_list = agent.get_liquidation_trades(self.market)
            else:
                trade_list = agent.get_trade_list(self.market, self.pricing_model)
            for agent_trade in trade_list:  # execute trades
                wallet_deltas = self.market.trade_and_update(agent_trade, self.pricing_model)
                agent.update_wallet(wallet_deltas, self.market)
                logging.debug(
                    "agent #%g wallet deltas = \n%s",
                    agent.wallet.address,
                    wallet_deltas.__dict__,
                )
                agent.log_status_report()
                # TODO: Get simulator, market, pricing model, agent state strings and log
                self.update_simulation_state()
                self.run_trade_number += 1

    def run_simulation(self) -> None:
        r"""
        Run the trade simulation and update the output state dictionary
        This is the primary function of the Simulator class.
        The PricingModel and Market objects will be constructed.
        A loop will execute a group of trades with random volumes and directions for each day,
        up to `self.config.simulator.num_trading_days` days.

        Returns
        -------
        There are no returns, but the function does update the simulation_state member variable
        """
        last_block_in_sim = False
        self.start_time = time_utils.current_datetime()
        for day in range(0, self.config.simulator.num_trading_days):
            self.day = day
            self.market.market_state.vault_apr = self.random_variables.vault_apr[self.day]
            # Vault return can vary per day, which sets the current price per share
            if self.day > 0:  # Update only after first day (first day set to init_share_price)
                if self.config.simulator.compound_vault_apr:  # Apply return to latest price (full compounding)
                    price_multiplier = self.market.market_state.share_price
                else:  # Apply return to starting price (no compounding)
                    price_multiplier = self.market.market_state.init_share_price
                delta = MarketDeltas(
                    d_share_price=(
                        self.market.market_state.vault_apr  # current day's apy
                        / 365  # convert annual yield to daily
                        * price_multiplier
                    )
                )
                self.market.update_market(delta)
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

    def update_simulation_state(self) -> None:
        """Increment the list for each key in the simulation_state output variable"""
        # pylint: disable=too-many-statements
        self.simulation_state.model_name.append(self.pricing_model.model_name())
        self.simulation_state.run_number.append(self.run_number)
        self.simulation_state.simulation_start_time.append(self.start_time)
        self.simulation_state.day.append(self.day)
        self.simulation_state.block_number.append(self.block_number)
        self.simulation_state.daily_block_number.append(self.daily_block_number)
        self.simulation_state.block_timestamp.append(
            time_utils.block_number_to_datetime(self.start_time, self.block_number, self.time_between_blocks)
            if self.start_time
            else "None"
        )
        self.simulation_state.current_market_datetime.append(
            time_utils.yearfrac_as_datetime(self.start_time, self.market.time) if self.start_time else "None"
        )
        self.simulation_state.current_market_yearfrac.append(self.market.time)
        self.simulation_state.run_trade_number.append(self.run_trade_number)
        self.simulation_state.market_step_size.append(self.market_step_size())
        self.simulation_state.position_duration.append(self.market.position_duration)
        self.simulation_state.target_liquidity.append(self.random_variables.target_liquidity)
        self.simulation_state.fee_percent.append(self.market.fee_percent)
        self.simulation_state.floor_fee.append(self.config.amm.floor_fee)
        self.simulation_state.init_vault_age.append(self.random_variables.init_vault_age)
        self.simulation_state.base_asset_price.append(self.config.market.base_asset_price)
        self.simulation_state.pool_apr.append(self.market.get_rate(self.pricing_model))
        self.simulation_state.num_trading_days.append(self.config.simulator.num_trading_days)
        self.simulation_state.num_blocks_per_day.append(self.config.simulator.num_blocks_per_day)
        self.simulation_state.update_market_state(self.market.market_state)
        for agent in self.agents.values():
            self.simulation_state.update_agent_wallet(self.run_trade_number, agent)
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        if self.market.market_state.share_reserves > 0:  # there is money in the market
            self.simulation_state.spot_price.append(self.market.get_spot_price(self.pricing_model))
        else:
            self.simulation_state.spot_price.append(np.nan)
