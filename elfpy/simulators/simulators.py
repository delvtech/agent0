"""Simulator class wraps the pricing models and markets for experiment tracking and execution"""
from __future__ import annotations
import logging
from typing import TYPE_CHECKING

import numpy as np
from numpy.random._generator import Generator as NumpyGenerator

import elfpy.time as time
import elfpy.types as types

from elfpy.agents.get_wallet_state import get_wallet_state
from elfpy.markets.hyperdrive.hyperdrive_market_deltas import HyperdriveMarketDeltas
from elfpy.math import FixedPoint
from elfpy.simulators.config import Config
from elfpy.simulators.simulation_state import (
    BlockSimVariables,
    DaySimVariables,
    NewSimulationState,
    RunSimVariables,
    SimulationState,
    TradeSimVariables,
)

if TYPE_CHECKING:
    from elfpy.agents.agent import Agent
    from elfpy.markets.hyperdrive.hyperdrive_market import HyperdriveMarket


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
        market: HyperdriveMarket,
        block_time: time.BlockTime,
    ):
        # User specified variables
        self.config = config.copy()
        logging.info("%s", self.config)
        self.market = market
        self.block_time = block_time
        self.set_rng(config.rng)
        self.config.check_variable_apr()
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
        self.trade_number = 0
        if self.config.do_dataframe_states:
            self.new_simulation_state = NewSimulationState()
        self.simulation_state = SimulationState()

    def set_rng(self, rng: NumpyGenerator) -> None:
        r"""Assign the internal random number generator to a new instantiation
        This function is useful for forcing identical trade volume and directions across simulation runs

        Arguments
        ----------
        rng : Generator
            Random number generator, constructed using np.random.default_rng(seed)
        """
        if not isinstance(rng, NumpyGenerator):
            raise TypeError(f"rng type must be a random number generator, not {type(rng)}.")
        self.rng = rng

    def get_simulation_state_string(self) -> str:
        r"""Returns a formatted string containing all of the Simulation class member variables

        Returns
        -------
        state_string : str
            Simulator class member variables (keys & values in self.__dict__) cast to a string, separated by a new line
        """
        if self.config.do_dataframe_states:
            return str(self.new_simulation_state)
        strings = [
            f"{attribute} = {value}"
            for attribute, value in self.__dict__.items()
            if attribute not in ("simulation_state", "rng")
        ]
        return "\n".join(strings)

    @property
    def time_step(self) -> float:
        r"""Returns minimum time increment in years

        Returns
        -------
        float
            time between blocks, which is computed as 1 / blocks_per_year
        """
        blocks_per_year = 365 * self.config.num_blocks_per_day
        return 1 / blocks_per_year

    def add_agents(self, agent_list: list[Agent]) -> None:
        r"""Append the agents and simulation_state member variables

        If trades have already happened (as indicated by self.trade_number), then empty wallet states are
        prepended to the simulation_state for each new agent so that the state can still easily be converted into
        a pandas dataframe.

        Arguments
        ----------
        agent_list : list[Agent]
            A list of instantiated Agent objects
        """
        for agent in agent_list:
            self.agents.update({agent.wallet.address: agent})
            for key in agent.wallet.get_state_keys():
                setattr(self.simulation_state, key, [None] * self.trade_number)

    def collect_and_execute_trades(self, liquidate: bool = False) -> None:
        r"""Get trades from the agent list, execute them, and update states

        Arguments
        ----------
        liquidate : bool
            If True, indicates if the current set of trades should be considered the final trades,
            e.g. they are occuring on the final block in the simulation
        """
        if self.config.shuffle_users:
            if liquidate:
                agent_ids: list[int] = self.rng.permutation(  # shuffle wallets except init_lp
                    [key for key in self.agents if key > 0]  # exclude init_lp before shuffling
                ).tolist()
                if self.config.init_lp:
                    agent_ids.append(0)  # add init_lp so that they're always last
            else:
                agent_ids = self.rng.permutation(
                    list(self.agents)
                ).tolist()  # random permutation of keys (agent wallet addresses)
        else:  # we are in a deterministic mode
            agent_ids = list(self.agents)[::-1] if liquidate else list(self.agents)
        # Collect trades from all of the agents.
        # TODO: This API causes a unnecessary double loop; first over agents, then trades,
        #       then we loop again over all trades. In the future we want to simulate something like
        #       the mempool, which has all agent trades. But for now it would be better if we could
        #       get all of the block's trades without an extra loop.
        trades = self.collect_trades(agent_ids, liquidate)
        # Execute the trades
        if len(trades) > 0:
            self.execute_trades(trades)

    def collect_trades(self, agent_ids: list[int], liquidate: bool = False) -> list[tuple[int, types.Trade]]:
        r"""Collect trades from a set of provided agent IDs.

        Arguments
        ----------
        agent_ids : list[int]
            A list of agent IDs. These IDs must correspond to agents that are
            registered in the simulator.

        liquidate : bool
            If true, have agents collect their liquidation trades. Otherwise, agents collect their normal trades.

        Returns
        -------
        list[tuple[int, Trade]]
            A list of trades associated with specific agents.
        """
        agents_and_trades: list[tuple[int, types.Trade]] = []
        for agent_id in agent_ids:
            agent = self.agents[agent_id]
            if liquidate:
                logging.debug("Collecting liquiditation trades for market closure")
                trades = agent.get_liquidation_trades(self.market)
            else:
                trades = agent.get_trades(self.market)
            agents_and_trades.extend((agent_id, trade) for trade in trades)
        return agents_and_trades

    def execute_trades(self, agent_actions: list[tuple[int, types.Trade]]) -> None:
        r"""Execute a list of trades associated with agents in the simulator.

        Arguments
        ----------
        trades : list[tuple[int, list[Trade]]]
            A list of agent trades. These will be executed in order.
            for trade in trades:
                trade[0] is the agent wallet address;
                trade[1].market is the trade market;
                trade[1].trade is the action
        """
        for trade in agent_actions:
            # TODO: After we implement support for multiple markets,
            # we will decompose the trade into the agent ID, market,
            # and market action before sending the info off to the
            # correct market. This way, for example, a trade can happen
            # on the borrow market OR the hyperdrive market.
            action_details = (trade[0], trade[1].trade)
            market_state_before_trade = self.market.market_state.copy()
            try:
                agent_id, agent_deltas, market_deltas = self.market.perform_action(action_details)
            except (ValueError, AssertionError) as err:
                self.market.market_state = market_state_before_trade
                logging.debug(
                    "TRADE FAILED %s\npre_trade_market = %s\nerror = %s",
                    action_details[1],
                    self.market.market_state,
                    err,
                )
                continue
            self.agents[agent_id].log_status_report()
            # TODO: need to log deaggregated trade informaiton, i.e. trade_deltas
            # issue #215
            self.update_simulation_state()
            if self.config.do_dataframe_states:
                self.new_simulation_state.update(
                    trade_vars=TradeSimVariables(
                        self.run_number,
                        self.day,
                        self.block_number,
                        self.trade_number,
                        float(self.market.fixed_apr),
                        float(self.market.spot_price),
                        trade[1].trade,
                        market_deltas,
                        agent_id,
                        agent_deltas,
                    )
                )
            self.trade_number += 1

    def run_simulation(self, liquidate_on_end: bool = True) -> None:
        r"""Run the trade simulation and update the output state dictionary

        This helper function advances time and orchestrates trades.
        Typically, the simulation executes as follows:

        .. code-block::
           for day in num_trading_days:
               # update simulation state day variables
               for block in num_blocks_per_day:
                   # update simulation state block variables
                   for agent in agents:
                       for trade in agent.trades:
                           # do_trade
                           # update simulation state trade variables

        Arguments
        ----------
        liquidate_on_end : bool
            if True, liquidate trades when the simulation is complete
        """
        last_block_in_sim = False
        if self.config.do_dataframe_states:
            self.new_simulation_state.update(
                run_vars=RunSimVariables(
                    run_number=self.run_number,
                    config=self.config,
                    agent_init=[agent.wallet for agent in self.agents.values()],
                    market_init=self.market.market_state,
                    time_step=self.time_step,
                    position_duration=self.market.position_duration,
                )
            )
        for day in range(self.config.num_trading_days):
            self.day = day
            self.market.market_state.variable_apr = FixedPoint(self.config.variable_apr[self.day])
            # Vault return can vary per day, which sets the current price per share
            if self.day > 0:  # Update only after first day (first day set to init_share_price)
                if self.config.compound_variable_apr:  # Apply return to latest price (full compounding)
                    price_multiplier = self.market.market_state.share_price
                else:  # Apply return to starting price (no compounding)
                    price_multiplier = self.market.market_state.init_share_price
                delta = HyperdriveMarketDeltas(
                    d_share_price=(
                        self.market.market_state.variable_apr  # current day's apy
                        / FixedPoint("365.0")  # convert annual yield to daily
                        * price_multiplier
                    )
                )
                self.market.update_market(delta)
            if self.config.do_dataframe_states:
                self.new_simulation_state.update(
                    day_vars=DaySimVariables(
                        self.run_number,
                        self.day,
                        float(self.market.market_state.variable_apr),
                        float(self.market.market_state.share_price),
                    )
                )
            for daily_block_number in range(self.config.num_blocks_per_day):
                self.daily_block_number = daily_block_number
                last_block_in_sim = (self.day == self.config.num_trading_days - 1) and (
                    self.daily_block_number == self.config.num_blocks_per_day - 1
                )
                liquidate = last_block_in_sim and liquidate_on_end
                if self.config.do_dataframe_states:
                    self.new_simulation_state.update(
                        block_vars=BlockSimVariables(
                            self.run_number, self.day, self.block_number, float(self.block_time.time)
                        )
                    )
                self.collect_and_execute_trades(liquidate)
                logging.debug(
                    "day = %g, daily_block_number = %g, block_time = %g\n",
                    self.day,
                    self.daily_block_number,
                    self.block_time.time,
                )
                if not last_block_in_sim:
                    self.block_time.tick(FixedPoint(self.time_step))
                    self.block_number += 1
        # simulation has ended
        for agent in self.agents.values():
            agent.log_final_report(self.market)

    def update_simulation_state(self) -> None:
        r"""Increment the list for each key in the simulation_state output variable

        .. todo:: This gets duplicated in notebooks when we make the pandas dataframe.
            Instead, the simulation_state should be a dataframe.
            issue #215
        """
        # pylint: disable=too-many-statements
        self.simulation_state.model_name.append(self.market.pricing_model.model_name())
        self.simulation_state.run_number.append(self.run_number)
        self.simulation_state.day.append(self.day)
        self.simulation_state.block_number.append(self.block_number)
        self.simulation_state.daily_block_number.append(self.daily_block_number)
        self.simulation_state.current_time.append(float(self.block_time.time))
        self.simulation_state.trade_number.append(self.trade_number)
        self.simulation_state.time_step_size.append(self.time_step)
        self.simulation_state.position_duration.append(self.market.position_duration.astype(float))  # type: ignore
        self.simulation_state.fixed_apr.append(float(self.market.fixed_apr))
        self.simulation_state.current_variable_apr.append(self.config.variable_apr[self.day])
        self.simulation_state.add_dict_entries({"config." + key: val for key, val in self.config.__dict__.items()})
        self.simulation_state.add_dict_entries(self.market.market_state.__dict__)
        for agent in self.agents.values():
            self.simulation_state.add_dict_entries(get_wallet_state(agent.wallet, self.market))
        # TODO: This is a HACK to prevent test_sim from failing on market shutdown
        # when the market closes, the share_reserves are 0 (or negative & close to 0) and several logging steps break
        if self.market.market_state.share_reserves > FixedPoint(0):  # there is money in the market
            self.simulation_state.spot_price.append(float(self.market.spot_price))
        else:
            self.simulation_state.spot_price.append(np.nan)
