from __future__ import annotations  # types will be strings by default in 3.11

import logging
from typing import TYPE_CHECKING
<<<<<<< HEAD
from dataclasses import dataclass, field, make_dataclass
=======
from functools import wraps
from dataclasses import dataclass, field
<<<<<<< HEAD
>>>>>>> 98dc865 (fixes circular imports)
from enum import Enum
=======
>>>>>>> 3966505 (getting started on the rest of the refactor)
import json

import pandas as pd
import numpy as np
from numpy.random import Generator

import elfpy.utils.time as time_utils
import elfpy.utils.outputs as output_utils

if TYPE_CHECKING:
    from elfpy.markets.hyperdrive import MarketTradeResult
    from datetime import datetime
    from typing import Type, Any, Optional


def to_description(description: str) -> dict[str, str]:
    r"""A dataclass helper that constructs metadata containing a description."""
    return {"description": description}


def freezable(frozen: bool = False, no_new_attribs: bool = False) -> Type:
    r"""A wrapper that allows classes to be frozen, such that existing member attributes cannot be changed"""

    def decorator(cls: Type) -> Type:
        @wraps(wrapped=cls, updated=())
        class FrozenClass(cls):
            """Subclass cls to enable freezing of attributes

            .. todo:: resolve why pyright cannot access member "freeze" when instantiated_class.freeze() is called
            """

            def __init__(self, *args, frozen=frozen, no_new_attribs=no_new_attribs, **kwargs) -> None:
                super().__init__(*args, **kwargs)
                super().__setattr__("frozen", frozen)
                super().__setattr__("no_new_attribs", no_new_attribs)

            def __setattr__(self, attrib: str, value: Any) -> None:
                if hasattr(self, attrib) and hasattr(self, "frozen") and getattr(self, "frozen"):
                    raise AttributeError(f"{self.__class__.__name__} is frozen, cannot change attribute '{attrib}'.")
                if not hasattr(self, attrib) and hasattr(self, "no_new_attribs") and getattr(self, "no_new_attribs"):
                    raise AttributeError(
                        f"{self.__class__.__name__} has no_new_attribs set, cannot add attribute '{attrib}'."
                    )
                super().__setattr__(attrib, value)

            def freeze(self) -> None:
                """disallows changing existing members"""
                super().__setattr__("frozen", True)

            def disable_new_attribs(self) -> None:
                """disallows adding new members"""
                super().__setattr__("no_new_attribs", True)

        return FrozenClass

    return decorator


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
    position_duration: list[StretchedTime] = field(
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
    position_duration: StretchedTime = field(
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
    agent_deltas: Wallet = field(metadata=to_description("deltas used to update the market state"))


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
