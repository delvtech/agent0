"""Dataclass for storing the current and past simulation state"""
from __future__ import annotations
from dataclasses import dataclass, field, make_dataclass
from typing import Optional, TYPE_CHECKING

import pandas as pd

import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.time as time
import elfpy.types as types

from elfpy.markets.hyperdrive.hyperdrive_market_deltas import HyperdriveMarketDeltas
from elfpy.simulators.config import Config

if TYPE_CHECKING:
    from elfpy.agents.agent_deltas import AgentDeltas
    from elfpy.agents.wallet import Wallet


@dataclass
class SimulationState:
    r"""Simulator state, updated after each trade

    MarketState, Agent, and Config attributes are added dynamically in Simulator.update_simulation_state()
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    # the name of the pricing model that is used in simulation"
    model_name: list[str] = field(default_factory=list)
    # simulation index
    run_number: list[int] = field(default_factory=list)
    # day index in a given simulation
    day: list[int] = field(default_factory=list)
    # block index in a given simulation
    block_number: list[int] = field(default_factory=list)
    # block index in a given day
    daily_block_number: list[int] = field(default_factory=list)
    # current block time in years
    current_time: list[float] = field(default_factory=list)
    # trade number in a given simulation
    trade_number: list[int] = field(default_factory=list)
    # minimum time discretization for a time step
    time_step_size: list[float] = field(default_factory=list)
    # time lapse between token mint and expiry in years
    position_duration: list[time.StretchedTime] = field(default_factory=list)
    # variable apr on a given day
    current_variable_apr: list[float] = field(default_factory=list)
    # apr of the AMM pool
    fixed_apr: list[float] = field(default_factory=list)
    # price of shares
    spot_price: list[float] = field(default_factory=list)

    def add_dict_entries(self, dictionary: dict) -> None:
        r"""Adds keys & values of input ditionary to the simulation state
        The simulation state is an ever-growing list,
        so each item in this dict is appended to the attribute with a corresponding key.
        If no attribute exists for that key, a new list containing the value is assigned to the attribute
        Arguments
        ----------
        dictionary : dict
            items to be added
        """
        for key, val in dictionary.items():
            if key in ["frozen", "no_new_attribs"]:
                continue
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


def simulation_state_aggreagator(constructor):
    """Returns a dataclass that aggregates simulation state attributes"""
    # Wrap the type from the constructor in a list, but keep the name
    attribs = [(str(key), list[val], field(default_factory=list)) for key, val in constructor.__annotations__.items()]

    # Make a new dataclass that has helper functions for appending to the list
    def update(obj, dictionary):
        for key, value in dictionary.items():
            obj.update_item(key, value)

    # The lambda is used because of the self variable -- TODO: can possibly remove?
    # pylint: disable=unnecessary-lambda
    aggregator = make_dataclass(
        cls_name=constructor.__name__ + "Aggregator",
        fields=attribs,
        namespace={
            "update_item": lambda self, key, value: getattr(self, key).append(value),
            "update": lambda self, dict_like: update(self, dict_like),
        },
    )()
    return aggregator


@dataclass
class RunSimVariables:
    """Simulation state variables that change by run"""

    # incremented each time run_simulation is called
    run_number: int
    # the simulation config
    config: Config
    # initial wallets for the agents
    agent_init: list[Wallet]
    # initial market state for this simulation run
    market_init: hyperdrive_market.HyperdriveMarketState
    # minimum time discretization for time step in years
    time_step: float
    # time lapse between token mint and expiry in years
    position_duration: time.StretchedTime


@dataclass
class DaySimVariables:
    """Simulation state variables that change by day"""

    # incremented each time run_simulation is called
    run_number: int
    # day index in a given simulation
    day: int
    # variable apr on a given day
    variable_apr: float
    # share price for the underlying vault
    share_price: float


@dataclass
class BlockSimVariables:
    """Simulation state variables that change by block"""

    # incremented each time run_simulation is called
    run_number: int
    # day index in a given simulation
    day: int
    # integer, block index in a given simulation
    block_number: int
    # float, current time in years
    time: float


@dataclass
class TradeSimVariables:
    """Simulation state variables that change by trade"""

    # pylint: disable=too-many-instance-attributes

    # incremented each time run_simulation is called
    run_number: int
    # day index in a given simulation
    day: int
    # block index in a given simulation
    block_number: int
    # trade number in a given simulation
    trade_number: int
    # apr of the AMM pool
    fixed_apr: float
    # price of shares
    spot_price: float
    # trade being executed
    trade_action: types.Trade
    # deltas used to update the market state
    market_deltas: HyperdriveMarketDeltas
    # address of the agent that is executing the trade
    agent_address: int
    # deltas used to update the market state
    agent_deltas: AgentDeltas


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
