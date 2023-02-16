"""Simulator class wraps the pricing models and markets for experiment tracking and execution"""
from __future__ import annotations  # types will be strings by default in 3.11

from typing import TYPE_CHECKING
import datetime
import logging

import numpy as np
from numpy.random._generator import Generator

import elfpy.utils.time as time_utils
from elfpy.types import MarketAction, MarketDeltas, SimulationState

if TYPE_CHECKING:
    from elfpy.agent import Agent
    from elfpy.markets import Market
    from elfpy.types import Config


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
    ):
        # User specified variables
        self.config = config
        logging.info("%s", self.config)
        self.market = market
        self.set_rng(config.rng)
        self.config.check_vault_apr()
        # NOTE: lint error false positives: This message may report object members that are created dynamically,
        # but exist at the time they are accessed.
        self.config.freeze()  # type: ignore
        self.agents: dict[int, Agent] = {}

        # Simulation variables
        self.run_number = 0
        self.day = 0
        self.block_number = 0
        self.daily_block_number = 0
        seconds_in_a_day = 86400
        self.time_between_blocks = seconds_in_a_day / self.config.num_blocks_per_day
        self.run_trade_number = 0
        self.start_time: datetime.datetime | None = None
        self.simulation_state = SimulationState()

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
        blocks_per_year = 365 * self.config.num_blocks_per_day
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
            for key in agent.wallet.get_state_keys():
                setattr(self.simulation_state, key, [None] * self.run_trade_number)

    def collect_and_execute_trades(self, last_block_in_sim: bool = False) -> None:
        r"""Get trades from the agent list, execute them, and update states

        Parameters
        ----------
        last_block_in_sim : bool
            If True, indicates if the current set of trades are occuring on the final block in the simulation
        """
        if self.config.shuffle_users:
            if last_block_in_sim:
                agent_ids = self.rng.permutation(  # shuffle wallets except init_lp
                    [key for key in self.agents if key > 0]  # exclude init_lp before shuffling
                ).tolist()
                if self.config.init_lp:
                    agent_ids = np.append(agent_ids, 0)  # add init_lp so that they're always last
            else:
                agent_ids = self.rng.permutation(
                    list(self.agents)
                ).tolist()  # random permutation of keys (agent wallet addresses)
        else:  # we are in a deterministic mode
            if not last_block_in_sim:
                agent_ids = list(self.agents)  # execute in increasing order
            else:  # last block in sim
                # close their trades in reverse order to allow withdrawing of LP tokens
                agent_ids = list(self.agents)[::-1]
        # Collect trades from all of the agents.
        trades = self.collect_trades(agent_ids, liquidate=last_block_in_sim)
        # Execute the trades.
        self.execute_trades(trades)

    def collect_trades(self, agent_ids: list[int], liquidate: bool = False) -> list[tuple[int, MarketAction]]:
        r"""Collect trades from a set of provided agent IDs.

        Parameters
        ----------
        agent_ids : list[int]
            A list of agent IDs. These IDs must correspond to agents that are
            registered in the simulator.

        Returns
        -------
        list[tuple[int, list[MarketAction]]]
            A list of trades associated with specific agents.
        """
        agents_and_trades = []
        for agent_id in agent_ids:
            agent = self.agents[agent_id]
            if liquidate:
                logging.debug("Collecting liquiditation trades for market closure")
                trades = agent.get_liquidation_trades(self.market)
            else:
                trades = agent.get_trades(self.market)
            for trade in trades:
                agents_and_trades.append((agent_id, trade))
        return agents_and_trades

    def execute_trades(self, agent_trades: list[tuple[int, MarketAction]]) -> None:
        r"""Execute a list of trades associated with agents in the simulator.

        Parameters
        ----------
        trades : list[tuple[int, list[MarketAction]]]
            A list of agent trades. These will be executed in order.
        """
        for trade in agent_trades:
            agent_id, agent_deltas = self.market.trade_and_update(trade)
            agent = self.agents[agent_id]
            logging.debug(
                "agent #%g wallet deltas:\n%s",
                agent.wallet.address,
                agent_deltas,
            )
            agent.update_wallet(agent_deltas, self.market)
            agent.log_status_report()
            # TODO: Get simulator, market, pricing model, agent state strings and log
            # TODO: need to log deaggregated trade informaiton, i.e. trade_deltas
            self.update_simulation_state()
            self.run_trade_number += 1

    def run_simulation(self) -> None:
        r"""Run the trade simulation and update the output state dictionary

        This is the primary function of the Simulator class.
        The PricingModel and Market objects will be constructed.
        A loop will execute a group of trades with random volumes and directions for each day,
        up to `self.config.num_trading_days` days.

        Returns
        -------
        There are no returns, but the function does update the simulation_state member variable
        """
        last_block_in_sim = False
        self.start_time = time_utils.current_datetime()
        for day in range(0, self.config.num_trading_days):
            self.day = day
            self.market.market_state.vault_apr = self.config.vault_apr[self.day]
            # Vault return can vary per day, which sets the current price per share
            if self.day > 0:  # Update only after first day (first day set to init_share_price)
                if self.config.compound_vault_apr:  # Apply return to latest price (full compounding)
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
            for daily_block_number in range(self.config.num_blocks_per_day):
                self.daily_block_number = daily_block_number
                last_block_in_sim = (self.day == self.config.num_trading_days - 1) and (
                    self.daily_block_number == self.config.num_blocks_per_day - 1
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
        r"""Increment the list for each key in the simulation_state output variable

        TODO: This gets duplicated in notebooks when we make the pandas dataframe.
            Instead, the simulation_state should be a dataframe.
        """
        # pylint: disable=too-many-statements
        self.simulation_state.model_name.append(self.market.pricing_model.model_name())
        self.simulation_state.run_number.append(self.run_number)
        self.simulation_state.simulation_start_time.append(self.start_time)
        self.simulation_state.day.append(self.day)
        self.simulation_state.block_number.append(self.block_number)
        self.simulation_state.daily_block_number.append(self.daily_block_number)
        if self.start_time is None:
            self.simulation_state.block_timestamp.append(None)
            self.simulation_state.current_market_datetime.append(None)
        else:
            self.simulation_state.block_timestamp.append(
                time_utils.block_number_to_datetime(self.start_time, self.block_number, self.time_between_blocks)
            )
            self.simulation_state.current_market_datetime.append(
                time_utils.year_as_datetime(self.start_time, self.market.time)
            )
        self.simulation_state.current_market_time.append(self.market.time)
        self.simulation_state.run_trade_number.append(self.run_trade_number)
        self.simulation_state.market_step_size.append(self.market_step_size())
        self.simulation_state.position_duration.append(self.market.position_duration)
        self.simulation_state.pool_apr.append(self.market.apr)
        self.simulation_state.current_vault_apr.append(self.config.vault_apr[self.day])
        self.simulation_state.add_dict_entries({"config." + key: val for key, val in self.config.__dict__.items()})
        self.simulation_state.add_dict_entries(self.market.market_state.__dict__)
        for agent in self.agents.values():
            self.simulation_state.add_dict_entries(agent.wallet.get_state(self.market))
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        if self.market.market_state.share_reserves > 0:  # there is money in the market
            self.simulation_state.spot_price.append(self.market.spot_price)
        else:
            self.simulation_state.spot_price.append(np.nan)
