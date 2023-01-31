"""Simulator class wraps the pricing models and markets for experiment tracking and execution"""

from __future__ import annotations  # types will be strings by default in 3.11
from typing import Any, Optional, TYPE_CHECKING
import datetime
import json
import logging
import numpy as np
from numpy.random._generator import Generator

import elfpy.utils.time as time_utils
from elfpy.utils.outputs import CustomEncoder
from elfpy.types import MarketAction, MarketDeltas, RandomSimulationVariables, SimulationState
from elfpy.utils import config as config_utils

if TYPE_CHECKING:
    from elfpy.agent import Agent
    from elfpy.markets import Market
    from elfpy.utils.config import Config


class Simulator:
    r"""Stores environment variables & market simulation outputs for AMM experimentation

    Member variables include input settings, random variable ranges, and simulation outputs.
    To be used in conjunction with the Market and PricingModel classes
    """

    # TODO: set up member (dataclass?) object that owns attributes instead of so many individual instance attributes
    # pylint: disable=too-many-instance-attributes

    def __init__(
        self,
        config: Config,
        market: Market,
        random_simulation_variables: Optional[RandomSimulationVariables] = None,
    ):
        # User specified variables
        self.config = config
        self.log_config_variables()
        self.market = market
        self.set_rng(config.simulator.rng)
        if random_simulation_variables is None:
            self.random_variables = config_utils.get_random_variables(self.config)
        else:
            self.random_variables = random_simulation_variables
        self.check_vault_apr()
        self.agents = {}

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

    def check_vault_apr(self) -> None:
        r"""Verify that the vault_apr is the right length"""
        if not len(self.random_variables.vault_apr) == self.config.simulator.num_trading_days:
            raise ValueError(
                "vault_apr must have len equal to num_trading_days = "
                + f"{self.config.simulator.num_trading_days},"
                + f" not {len(self.random_variables.vault_apr)}"
            )

    def set_rng(self, rng: Generator) -> None:
        r"""Assign the internal random number generator to a new instantiation
        This function is useful for forcing identical trade volume and directions across simulation runs

        Parameters
        ----------
        rng : Generator
            Random number generator, constructed using np.random.default_rng(seed)
        """
        if not isinstance(rng, Generator):
            raise TypeError(f"rng type must be a random number generator, not {type(rng)}.")
        self.rng = rng

    def log_config_variables(self) -> None:
        r"""Prints all variables that are in config"""
        # cls arg tells json how to handle numpy objects and nested dataclasses
        config_string = json.dumps(self.config.__dict__, sort_keys=True, indent=2, cls=CustomEncoder)
        logging.info(config_string)

    def get_simulation_state_string(self) -> str:
        r"""Returns a formatted string containing all of the Simulation class member variables

        Returns
        -------
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
        r"""Returns minimum time increment

        Returns
        -------
        float
            time between blocks, which is computed as 1 / blocks_per_year
        """
        blocks_per_year = 365 * self.config.simulator.num_blocks_per_day
        return 1 / blocks_per_year

    def add_agents(self, agent_list: list[Agent]) -> None:
        r"""Append the agents and simulation_state member variables

        If trades have already happened (as indicated by self.run_trade_number), then empty wallet states are
        prepended to the simulation_state for each new agent so that the state can still easily be converted into
        a pandas dataframe.

        Parameters
        ----------
        agent_list : list[Agent]
            A list of instantiated Agent objects
        """
        for agent in agent_list:
            self.agents.update({agent.wallet.address: agent})
            for key in agent.wallet.state:
                setattr(self.simulation_state, key, [None] * self.run_trade_number)

    def collect_and_execute_trades(self, last_block_in_sim: bool = False) -> None:
        r"""Get trades from the agent list, execute them, and update states

        Parameters
        ----------
        last_block_in_sim : bool
            If True, indicates if the current set of trades are occuring on the final block in the simulation
        """
        if self.config.simulator.shuffle_users:
            if last_block_in_sim:
                agent_ids = self.rng.permutation(  # shuffle wallets except init_lp
                    [key for key in self.agents if key > 0]  # exclude init_lp before shuffling
                )
                agent_ids = np.append(agent_ids, 0)  # add init_lp so that they're always last
            else:
                agent_ids = self.rng.permutation(
                    list(self.agents)
                )  # random permutation of keys (agent wallet addresses)
        else:  # we are in a deterministic mode
            if not last_block_in_sim:
                agent_ids = list(self.agents)  # execute in increasing order
            else:  # last block in sim
                # close their trades in reverse order to allow withdrawing of LP tokens
                agent_ids = list(self.agents)[::-1]

        # Collect trades from all of the agents.
        if last_block_in_sim:
            trades = self.collect_liquidation_trades(agent_ids)
        else:
            trades = self.collect_trades(agent_ids)

        # Execute the trades.
        self.execute_trades(trades)

    def collect_trades(self, agent_ids: Any) -> list[tuple[int, list[MarketAction]]]:
        r"""Collect trades from a set of provided agent IDs.

        Parameters
        ----------
        agent_ids : Any
            A list of agent IDs. These IDs must correspond to agents that are
            registered in the simulator.

        Returns
        -------
        list[tuple[int, list[MarketAction]]]
            A list of trades associated with specific agents.
        """
        return [(agent_id, self.agents[agent_id].get_trades(self.market)) for agent_id in agent_ids]

    def collect_liquidation_trades(self, agent_ids: Any) -> list[tuple[int, list[MarketAction]]]:
        r"""Collect liquidation trades from a set of provided agent IDs.

        Parameters
        ----------
        agent_ids : Any
            A list of agent IDs. These IDs must correspond to agents that are
            registered in the simulator.

        Returns
        -------
        list[tuple[int, list[MarketAction]]]
            A list of liquidation trades associated with specific agents.
        """
        return [(agent_id, self.agents[agent_id].get_liquidation_trades(self.market)) for agent_id in agent_ids]

    def execute_trades(self, trades: list[tuple[int, list[MarketAction]]]) -> None:
        r"""Execute a list of trades associated with agents in the simulator.

        Parameters
        ----------
        trades : list[tuple[int, list[MarketAction]]]
            A list of agent trades. These will be executed in order.
        """
        for (agent_id, agent_trades) in trades:
            agent = self.agents[agent_id]
            for trade in agent_trades:
                agent_deltas = self.market.trade_and_update(trade)
                agent.update_wallet(agent_deltas, self.market)
                logging.debug(
                    "agent #%g wallet deltas = \n%s",
                    agent.wallet.address,
                    agent_deltas.__dict__,
                )
                agent.log_status_report()
                # TODO: Get simulator, market, pricing model, agent state strings and log
                self.update_simulation_state()
                self.run_trade_number += 1

    def run_simulation(self) -> None:
        r"""Run the trade simulation and update the output state dictionary

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
                self.market.log_market_step_string()
                if not last_block_in_sim:
                    self.market.tick(self.market_step_size())
                    self.block_number += 1
        # simulation has ended
        for agent in self.agents.values():
            agent.log_final_report(self.market)

    def update_simulation_state(self) -> None:
        r"""Increment the list for each key in the simulation_state output variable"""
        # pylint: disable=too-many-statements
        self.simulation_state.model_name.append(self.market.pricing_model.model_name())
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
        self.simulation_state.trade_fee_percent.append(self.market.trade_fee_percent)
        self.simulation_state.redemption_fee_percent.append(self.market.redemption_fee_percent)
        self.simulation_state.floor_fee.append(self.config.amm.floor_fee)
        self.simulation_state.init_vault_age.append(self.random_variables.init_vault_age)
        self.simulation_state.base_asset_price.append(self.config.market.base_asset_price)
        self.simulation_state.pool_apr.append(self.market.rate)
        self.simulation_state.num_trading_days.append(self.config.simulator.num_trading_days)
        self.simulation_state.num_blocks_per_day.append(self.config.simulator.num_blocks_per_day)
        self.simulation_state.update_market_state(self.market.market_state)
        for agent in self.agents.values():
            self.simulation_state.update_agent_wallet(agent)
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        if self.market.market_state.share_reserves > 0:  # there is money in the market
            self.simulation_state.spot_price.append(self.market.spot_price)
        else:
            self.simulation_state.spot_price.append(np.nan)
