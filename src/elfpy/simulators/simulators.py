"""Simulator class wraps the pricing models and markets for experiment tracking and execution"""
from __future__ import annotations  # types will be strings by default in 3.11

from typing import TYPE_CHECKING, Optional
from datetime import datetime
import logging
import json
from dataclasses import dataclass, field, make_dataclass

import pandas as pd
import numpy as np
from numpy.random._generator import Generator

import elfpy.utils.time as time_utils
from elfpy.types import to_description, freezable
import elfpy.markets.hyperdrive as hyperdrive
import elfpy.utils.outputs as output_utils
import elfpy.agents.wallet as wallet

if TYPE_CHECKING:
    from elfpy.agents.agent import Agent
    from elfpy.markets.hyperdrive import Market, MarketAction, MarketDeltas


@dataclass
class SimulationState:
    r"""Simulator state, updated after each trade

    MarketState, Agent, and Config attributes are added dynamically in Simulator.update_simulation_state()

    .. todo:: change attribute type hints to indicate what list contents should be
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    model_name: list[str] = field(
        default_factory=list, metadata=to_description("the name of the pricing model that is used in simulation")
    )
    run_number: list[int] = field(default_factory=list, metadata=to_description("simulation index"))
    day: list[int] = field(default_factory=list, metadata=to_description("day index in a given simulation"))
    block_number: list[int] = field(
        default_factory=list, metadata=to_description("integer, block index in a given simulation")
    )
    daily_block_number: list[int] = field(
        default_factory=list, metadata=to_description("integer, block index in a given day")
    )
    simulation_start_time: list[Optional[datetime]] = field(
        default_factory=list, metadata=to_description("start datetime for a given simulation")
    )
    block_timestamp: list[Optional[datetime]] = field(
        default_factory=list, metadata=to_description("datetime of a given block's creation")
    )
    current_market_datetime: list[Optional[datetime]] = field(
        default_factory=list, metadata=to_description("float, current market time as a datetime")
    )
    current_market_time: list[float] = field(
        default_factory=list, metadata=to_description("float, current market time in years")
    )
    trade_number: list[int] = field(
        default_factory=list, metadata=to_description("integer, trade number in a given simulation")
    )
    market_step_size: list[float] = field(
        default_factory=list, metadata=to_description("minimum time discretization for market time step")
    )
    position_duration: list[time_utils.StretchedTime] = field(
        default_factory=list, metadata=to_description("time lapse between token mint and expiry as a yearfrac")
    )
    current_vault_apr: list[float] = field(default_factory=list, metadata=to_description("vault apr on a given day"))
    pool_apr: list[float] = field(default_factory=list, metadata=to_description("apr of the AMM pool"))
    spot_price: list[float] = field(default_factory=list, metadata=to_description("price of shares"))

    def add_dict_entries(self, dictionary: dict) -> None:
        r"""Adds keys & values of input ditionary to the simulation state

        The simulation state is an ever-growing list,
        so each item in this dict is appended to the attribute with a corresponding key.
        If no attribute exists for that key, a new list containing the value is assigned to the attribute

        Parameters
        ----------
        dictionary : dict
            items to be added
        """
        for key, val in dictionary.items():
            if hasattr(self, key):
                attribute_state = getattr(self, key)
                attribute_state.append(val)
                setattr(self, key, attribute_state)
            else:
                setattr(self, key, [val])

    def __getitem__(self, key):
        r"""Get object attribute referenced by `key`"""
        return getattr(self, key)

    def __setitem__(self, key, value):
        r"""Set object attribute referenced by `key` to `value`"""
        setattr(self, key, value)


@freezable(frozen=False, no_new_attribs=True)
@dataclass
class Config:
    """Data object for storing user simulation config parameters

    .. todo:: Rename the {trade/redemption}_fee_percent variables so that they doesn't use "percent"
    """

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    # Temporary
    do_dataframe_states: bool = False

    # Market
    target_liquidity: float = field(
        default=1e6, metadata=to_description("total size of the market pool (bonds + shares)")
    )
    target_volume: float = field(default=0.01, metadata=to_description("fraction of pool liquidity"))
    init_vault_age: float = field(default=0, metadata=to_description("fraction of a year since the vault was opened"))
    # NOTE: We ignore the type error since the value will never be None after
    # initialization, and we don't want the value to be set to None downstream.
    vault_apr: list[float] = field(  # default is overridden in __post_init__
        default_factory=lambda: [-1],
        metadata=to_description("the underlying (variable) vault APR at each time step"),
    )  # TODO: Move this out of config, it should be computed in simulator init based on config values
    init_share_price: float = field(  # default is overridden in __post_init__
        default=-1, metadata=to_description("initial market share price for the vault asset")  # type: ignore
    )  # TODO: Move this out of config, it should be computed in simulator init based on config values

    # AMM
    pricing_model_name: str = field(
        default="Hyperdrive", metadata=to_description('Must be "Hyperdrive", or "YieldSpace"')
    )
    trade_fee_percent: float = field(
        default=0.05, metadata=to_description("LP fee factor (decimal) to charge for trades")
    )
    redemption_fee_percent: float = field(
        default=0.05, metadata=to_description("LP fee factor (decimal) to charge for redemption")
    )
    target_pool_apr: float = field(default=0.1, metadata=to_description("desired fixed apr for as a decimal"))
    floor_fee: float = field(default=0, metadata=to_description("minimum fee percentage (bps)"))

    # Simulation
    # durations
    title: str = field(default="elfpy simulation", metadata=to_description("Text description of the simulation"))
    num_trading_days: int = field(default=3, metadata=to_description("in days; should be <= pool_duration"))
    num_blocks_per_day: int = field(default=3, metadata=to_description("int; agents execute trades each block"))
    num_position_days: int = field(
        default=90, metadata=to_description("time lapse between token mint and expiry as days")
    )

    # users
    shuffle_users: bool = field(
        default=True, metadata=to_description("Shuffle order of action (as if random gas paid)")
    )
    agent_policies: list = field(default_factory=list, metadata=to_description("List of strings naming user policies"))
    init_lp: bool = field(default=True, metadata=to_description("If True, use an initial LP agent to seed pool"))

    # vault
    compound_vault_apr: bool = field(
        default=True,
        metadata=to_description("Whether or not to use compounding revenue for the underlying yield source"),
    )

    # logging
    log_level: int = field(default=logging.INFO, metadata=to_description("Logging level, as defined by stdlib logging"))
    log_filename: str = field(default="simulation.log", metadata=to_description("filename for output logs"))

    # numerical
    precision: int = field(default=64, metadata=to_description("precision of calculations; max is 64"))

    # random
    random_seed: int = field(default=1, metadata=to_description("int to be used for the random seed"))
    rng: Generator = field(
        init=False, compare=False, metadata=to_description("random number generator used in the simulation")
    )

    def __post_init__(self) -> None:
        r"""init_share_price & rng are a function of other random variables"""
        self.rng = np.random.default_rng(self.random_seed)
        if self.vault_apr == [-1]:  # defaults to [-1] so this should happen right after init
            self.vault_apr = [0.05] * self.num_trading_days
        if self.init_share_price < 0:  # defaults to -1 so this should happen right after init
            self.init_share_price = (1 + self.vault_apr[0]) ** self.init_vault_age
        self.disable_new_attribs()  # disallow new attributes # pylint: disable=no-member # type: ignore

    def __getitem__(self, key) -> None:
        return getattr(self, key)

    def __setattr__(self, attrib, value) -> None:
        if attrib == "vault_apr":
            if hasattr(self, "vault_apr"):
                self.check_vault_apr()
            super().__setattr__("vault_apr", value)
        elif attrib == "init_share_price":
            super().__setattr__("init_share_price", value)
        else:
            super().__setattr__(attrib, value)

    def __str__(self) -> str:
        # cls arg tells json how to handle numpy objects and nested dataclasses
        config_string = json.dumps(self.__dict__, sort_keys=True, indent=2, cls=output_utils.CustomEncoder)
        return config_string

    def check_vault_apr(self) -> None:
        r"""Verify that the vault_apr is the right length"""
        if not isinstance(self.vault_apr, list):
            raise TypeError(
                f"ERROR: vault_apr must be of type list, not {type(self.vault_apr)}."
                f"\nhint: it must be set after Config is initialized."
            )
        if not hasattr(self, "num_trading_days") and len(self.vault_apr) != self.num_trading_days:
            raise ValueError(
                "ERROR: vault_apr must have len equal to num_trading_days = "
                + f"{self.num_trading_days},"
                + f" not {len(self.vault_apr)}"
            )


@dataclass
class RunSimVariables:
    """Simulation state variables that change by run"""

    run_number: int = field(metadata=to_description("incremented each time run_simulation is called"))
    config: Config = field(metadata=to_description("the simulation config"))
    market_step_size: float = field(metadata=to_description("minimum time discretization for market time step"))
    position_duration: time_utils.StretchedTime = field(
        metadata=to_description("time lapse between token mint and expiry as a yearfrac")
    )
    simulation_start_time: datetime = field(metadata=to_description("start datetime for a given simulation"))


@dataclass
class DaySimVariables:
    """Simulation state variables that change by day"""

    run_number: int = field(metadata=to_description("incremented each time run_simulation is called"))
    day: int = field(metadata=to_description("day index in a given simulation"))
    vault_apr: float = field(metadata=to_description("vault apr on a given day"))
    share_price: float = field(metadata=to_description("share price for the underlying vault"))


@dataclass
class BlockSimVariables:
    """Simulation state variables that change by block"""

    run_number: int = field(metadata=to_description("incremented each time run_simulation is called"))
    day: int = field(metadata=to_description("day index in a given simulation"))
    block_number: int = field(metadata=to_description("integer, block index in a given simulation"))
    market_time: float = field(metadata=to_description("float, current market time in years"))


@dataclass
class TradeSimVariables:
    """Simulation state variables that change by trade"""

    # pylint: disable=too-many-instance-attributes

    run_number: int = field(metadata=to_description("incremented each time run_simulation is called"))
    day: int = field(metadata=to_description("day index in a given simulation"))
    block_number: int = field(metadata=to_description("integer, block index in a given simulation"))
    trade_number: int = field(metadata=to_description("trade number in a given simulation"))
    pool_apr: float = field(metadata=to_description("apr of the AMM pool"))
    spot_price: float = field(metadata=to_description("price of shares"))
    market_deltas: MarketDeltas = field(metadata=to_description("deltas used to update the market state"))
    agent_address: int = field(metadata=to_description("address of the agent that is executing the trade"))
    agent_deltas: wallet.Wallet = field(metadata=to_description("deltas used to update the market state"))


def simulation_state_aggreagator(constructor):
    """Returns a dataclass that aggregates simulation state attributes"""
    # Wrap the type from the constructor in a list, but keep the name
    attribs = [
        (key, "list[" + val + "]", field(default_factory=list)) for key, val in constructor.__annotations__.items()
    ]
    # Make a new dataclass that has helper functions for appending to the list
    def update(obj, dictionary):
        for key, value in dictionary.items():
            obj.update_item(key, value)

    # The lambda is used because of the self variable -- TODO: can possibly remove?
    # pylint: disable=unnecessary-lambda
    aggregator = make_dataclass(
        constructor.__name__ + "Aggregator",
        attribs,
        namespace={
            "update_item": lambda self, key, value: getattr(self, key).append(value),
            "update": lambda self, dict_like: update(self, dict_like),
        },
    )()
    return aggregator


@dataclass
class NewSimulationState:
    r"""Simulator state that stores Market, Agent, and Config attributes
    The SimulationState has the following external attributes:
        run_updates: pd.DataFrame composed of RunSimVariables
        day_updates: pd.DataFrame composed of DaySimVariables
        block_updates: pd.DataFrame composed of BlockSimVariables
        trade_updates: pd.DataFrame composed of TradeSimVariables
    """

    def __post_init__(self) -> None:
        r"""Construct empty dataclasses with appropriate attributes for each state variable type"""
        self._run_updates = simulation_state_aggreagator(RunSimVariables)
        self._day_updates = simulation_state_aggreagator(DaySimVariables)
        self._block_updates = simulation_state_aggreagator(BlockSimVariables)
        self._trade_updates = simulation_state_aggreagator(TradeSimVariables)

    def update(
        self,
        run_vars: Optional[RunSimVariables] = None,
        day_vars: Optional[DaySimVariables] = None,
        block_vars: Optional[BlockSimVariables] = None,
        trade_vars: Optional[TradeSimVariables] = None,
    ) -> None:
        r"""Add a row to the state dataframes that contains the latest variables"""
        if run_vars is not None:
            self._run_updates.update(run_vars.__dict__)
        if day_vars is not None:
            self._day_updates.update(day_vars.__dict__)
        if block_vars is not None:
            self._block_updates.update(block_vars.__dict__)
        if trade_vars is not None:
            self._trade_updates.update(trade_vars.__dict__)

    @property
    def run_updates(self) -> pd.DataFrame:
        r"""Converts internal list of state values into a dataframe"""
        return pd.DataFrame.from_dict(self._run_updates.__dict__)

    @property
    def day_updates(self) -> pd.DataFrame:
        r"""Converts internal list of state values into a dataframe"""
        return pd.DataFrame.from_dict(self._day_updates.__dict__)

    @property
    def block_updates(self) -> pd.DataFrame:
        r"""Converts internal list of state values into a dataframe"""
        return pd.DataFrame.from_dict(self._block_updates.__dict__)

    @property
    def trade_updates(self) -> pd.DataFrame:
        r"""Converts internal list of state values into a dataframe"""
        return pd.DataFrame.from_dict(self._trade_updates.__dict__)

    @property
    def combined_dataframe(self) -> pd.DataFrame:
        r"""Returns a single dataframe that combines the run, day, block, and trade variables
        The merged dataframe has the same number of rows as self.trade_updates,
        with entries in the smaller dataframes duplicated accordingly
        """
        return self.trade_updates.merge(self.block_updates.merge(self.day_updates.merge(self.run_updates)))


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
        self.trade_number = 0
        self.start_time: datetime | None = None
        if self.config.do_dataframe_states:
            self.new_simulation_state = NewSimulationState()
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
        if self.config.do_dataframe_states:
            return str(self.new_simulation_state)
        strings = []
        for attribute, value in self.__dict__.items():
            if attribute not in ("simulation_state", "rng"):
                strings.append(f"{attribute} = {value}")
        state_string = "\n".join(strings)
        return state_string

    @property
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

        If trades have already happened (as indicated by self.trade_number), then empty wallet states are
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
                setattr(self.simulation_state, key, [None] * self.trade_number)

    def collect_and_execute_trades(self, last_block_in_sim: bool = False) -> None:
        r"""Get trades from the agent list, execute them, and update states

        Parameters
        ----------
        last_block_in_sim : bool
            If True, indicates if the current set of trades are occuring on the final block in the simulation
        """
        if self.config.shuffle_users:
            if last_block_in_sim:
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
            if not last_block_in_sim:
                agent_ids = list(self.agents)  # execute in increasing order
            else:  # last block in sim
                # close their trades in reverse order to allow withdrawing of LP tokens
                agent_ids = list(self.agents)[::-1]
        # Collect trades from all of the agents.
        trades = self.collect_trades(agent_ids, liquidate=last_block_in_sim)
        # Execute the trades
        self.execute_trades(trades)

    def collect_trades(self, agent_ids: list[int], liquidate: bool = False) -> list[tuple[int, MarketAction]]:
        r"""Collect trades from a set of provided agent IDs.

        Parameters
        ----------
        agent_ids: list[int]
            A list of agent IDs. These IDs must correspond to agents that are
            registered in the simulator.

        liquidate: bool
            If true, have agents collect their liquidation trades. Otherwise, agents collect their normal trades.


        Returns
        -------
        list[tuple[int, MarketAction]]
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
            agent_id, agent_deltas, market_deltas = self.market.trade_and_update(trade)
            self.market.update_market(market_deltas)
            agent = self.agents[agent_id]
            logging.debug(
                "agent #%g wallet deltas:\n%s",
                agent.wallet.address,
                agent_deltas,
            )
            agent.update_wallet(agent_deltas, self.market)
            # TODO: Get simulator, market, pricing model, agent state strings and log
            agent.log_status_report()
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
                        self.market.apr,
                        self.market.spot_price,
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

        Parameters
        ----------
        liquidate_on_end : bool
            if True, liquidate trades when the simulation is complete
        """
        last_block_in_sim = False
        self.start_time = time_utils.current_datetime()
        if self.config.do_dataframe_states:
            self.new_simulation_state.update(
                run_vars=RunSimVariables(
                    self.run_number, self.config, self.market_step_size, self.market.position_duration, self.start_time
                )
            )
        for day in range(0, self.config.num_trading_days):
            self.day = day
            self.market.market_state.vault_apr = self.config.vault_apr[self.day]
            # Vault return can vary per day, which sets the current price per share
            if self.day > 0:  # Update only after first day (first day set to init_share_price)
                if self.config.compound_vault_apr:  # Apply return to latest price (full compounding)
                    price_multiplier = self.market.market_state.share_price
                else:  # Apply return to starting price (no compounding)
                    price_multiplier = self.market.market_state.init_share_price
                delta = hyperdrive.MarketDeltas(
                    d_share_price=(
                        self.market.market_state.vault_apr  # current day's apy
                        / 365  # convert annual yield to daily
                        * price_multiplier
                    )
                )
                self.market.update_market(delta)
                if self.config.do_dataframe_states:
                    self.new_simulation_state.update(
                        day_vars=DaySimVariables(
                            self.run_number,
                            self.day,
                            self.market.market_state.vault_apr,
                            self.market.market_state.share_price,
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
                        block_vars=BlockSimVariables(self.run_number, self.day, self.block_number, self.market.time)
                    )
                self.collect_and_execute_trades(liquidate)
                logging.debug("day = %d, daily_block_number = %d\n", self.day, self.daily_block_number)
                self.market.log_market_step_string()
                if not last_block_in_sim:
                    self.market.tick(self.market_step_size)
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
        self.simulation_state.trade_number.append(self.trade_number)
        self.simulation_state.market_step_size.append(self.market_step_size)
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
