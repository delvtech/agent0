"""A set of common types used throughtout the simulation codebase"""
from __future__ import annotations  # types will be strings by default in 3.11

import logging
from functools import wraps
from typing import TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum
import json

import numpy as np
from numpy.random import Generator

from elfpy import PRECISION_THRESHOLD
import elfpy.utils.time as time_utils
from elfpy.utils.outputs import CustomEncoder
from elfpy.wallet import Wallet

if TYPE_CHECKING:
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


class TokenType(Enum):
    r"""A type of token"""

    BASE = "base"
    PT = "pt"


class MarketActionType(Enum):
    r"""
    The descriptor of an action in a market

    .. todo:: Add INITIALIZE_MARKET = "initialize_market"
    """

    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"

    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"


@dataclass
class Quantity:
    r"""An amount with a unit"""

    amount: float
    unit: TokenType


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class StretchedTime:
    r"""Stores time in units of days, as well as normalized & stretched variants

    .. todo:: Improve this constructor so that StretchedTime can be constructed from years.
    """
    days: float
    time_stretch: float
    normalizing_constant: float

    @property
    def stretched_time(self):
        r"""Returns days / normalizing_constant / time_stretch"""
        return time_utils.days_to_time_remaining(
            self.days, self.time_stretch, normalizing_constant=self.normalizing_constant
        )

    @property
    def normalized_time(self):
        r"""Format time as normalized days"""
        return time_utils.norm_days(
            self.days,
            self.normalizing_constant,
        )

    def __str__(self):
        output_string = (
            "StretchedTime(\n"
            f"\t{self.days=},\n"
            f"\t{self.normalized_time=},\n"
            f"\t{self.stretched_time=},\n"
            f"\t{self.time_stretch=},\n"
            f"\t{self.normalizing_constant=},\n"
            ")"
        )
        return output_string


@freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketAction:
    r"""Market action specification"""

    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    trade_amount: float
    # min amount to receive for the action
    min_amount_out: float
    # the agent's wallet
    wallet: Wallet
    # mint time is set only for trades that act on existing positions (close long or close short)
    mint_time: Optional[float] = None

    def __str__(self):
        r"""Return a description of the Action"""
        output_string = f"AGENT ACTION:\nagent #{self.wallet.address}"
        for key, value in self.__dict__.items():
            if key == "action_type":
                output_string += f" execute {value}()"
            elif key in ["trade_amount", "mint_time"]:
                output_string += f" {key}: {value}"
            elif key not in ["wallet_address", "agent"]:
                output_string += f" {key}: {value}"
        return output_string


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketDeltas:
    r"""Specifies changes to values in the market"""

    # .. todo::  Create our own dataclass decorator that is always mutable and includes dict set/get syntax
    # pylint: disable=duplicate-code
    # pylint: disable=too-many-instance-attributes

    # .. todo::  Use better naming for these values:
    #     - "d_base_asset" => "d_share_reserves"
    # .. todo::  Is there some reason this is base instead of shares?
    #     - "d_token_asset" => "d_bond_reserves"
    d_base_asset: float = 0
    d_token_asset: float = 0
    d_base_buffer: float = 0
    d_bond_buffer: float = 0
    d_lp_reserves: float = 0
    d_share_price: float = 0

    def __getitem__(self, key):
        return getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        output_string = (
            "MarketDeltas(\n"
            f"\t{self.d_base_asset=},\n"
            f"\t{self.d_token_asset=},\n"
            f"\t{self.d_base_buffer=},\n"
            f"\t{self.d_bond_buffer=},\n"
            f"\t{self.d_lp_reserves=},\n"
            f"\t{self.d_share_price=},\n"
            ")"
        )
        return output_string


@freezable(frozen=False, no_new_attribs=False)
@dataclass
class MarketState:
    r"""The state of an AMM

    Implements a class for all that that an AMM smart contract would hold or would have access to
    For example, reserve numbers are local state variables of the AMM.  The vault_apr will most
    likely be accessible through the AMM as well.

    Attributes
    ----------
    share_reserves: float
        Quantity of shares stored in the market
    bond_reserves: float
        Quantity of bonds stored in the market
    base_buffer: float
        Base amount set aside to account for open longs
    bond_buffer: float
        Bond amount set aside to account for open shorts
    lp_reserves: float
        Amount of lp tokens
    vault_apr: float
        .. todo: fill this in
    share_price: float
        .. todo: fill this in
    init_share_price: float
        .. todo: fill this in
    trade_fee_percent : float
        The percentage of the difference between the amount paid without
        slippage and the amount received that will be added to the input
        as a fee.
    redemption_fee_percent : float
        A flat fee applied to the output.  Not used in this equation for Yieldspace.
    """

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    # trading reserves
    share_reserves: float = 0.0
    bond_reserves: float = 0.0

    # trading buffers
    base_buffer: float = 0.0
    bond_buffer: float = 0.0

    # lp reserves
    lp_reserves: float = 0.0

    # share price
    vault_apr: float = 0.0
    share_price: float = 1.0
    init_share_price: float = 1.0

    # fee percents

    trade_fee_percent: float = 0.0
    redemption_fee_percent: float = 0.0

    def apply_delta(self, delta: MarketDeltas) -> None:
        r"""Applies a delta to the market state."""
        self.share_reserves += delta.d_base_asset / self.share_price
        self.bond_reserves += delta.d_token_asset
        self.base_buffer += delta.d_base_buffer
        self.bond_buffer += delta.d_bond_buffer
        self.lp_reserves += delta.d_lp_reserves
        self.share_price += delta.d_share_price

        # TODO: issue #146
        # this is an imperfect solution to rounding errors, but it works for now
        # ideally we'd find a more thorough solution than just catching errors
        # when they are.
        for key, value in self.__dict__.items():
            if 0 > value > -PRECISION_THRESHOLD:
                logging.debug(
                    ("%s=%s is negative within PRECISION_THRESHOLD=%f, setting it to 0"),
                    key,
                    value,
                    PRECISION_THRESHOLD,
                )
                setattr(self, key, 0)
            else:
                assert (
                    value > -PRECISION_THRESHOLD
                ), f"MarketState values must be > {-PRECISION_THRESHOLD}. Error on {key} = {value}"

    def copy(self) -> MarketState:
        """Returns a new copy of self"""
        return MarketState(
            share_reserves=self.share_reserves,
            bond_reserves=self.bond_reserves,
            base_buffer=self.bond_buffer,
            lp_reserves=self.lp_reserves,
            vault_apr=self.vault_apr,
            share_price=self.share_price,
            init_share_price=self.init_share_price,
            trade_fee_percent=self.trade_fee_percent,
            redemption_fee_percent=self.redemption_fee_percent,
        )

    def __str__(self):
        output_string = (
            "MarketState(\n"
            "\ttrading_reserves(\n"
            f"\t\t{self.share_reserves=},\n"
            f"\t\t{self.bond_reserves=},\n"
            "\t),\n"
            "\ttrading_buffers(\n"
            f"\t\t{self.base_buffer=},\n"
            f"\t\t{self.bond_buffer=},\n"
            "\t),\n"
            "\tlp_reserves(\n"
            f"\t\t{self.lp_reserves=},\n"
            "\t),\n"
            "\tunderlying_vault((\n"
            f"\t\t{self.vault_apr=},\n"
            f"\t\t{self.share_price=},\n"
            f"\t\t{self.init_share_price=},\n"
            "\t)\n"
            ")"
        )
        return output_string


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class AgentTradeResult:
    r"""The result to a user of performing a trade"""

    d_base: float
    d_bonds: float


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketTradeResult:
    r"""The result to a market of performing a trade"""

    d_base: float
    d_bonds: float


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class TradeBreakdown:
    r"""A granular breakdown of a trade.

    This includes information relating to fees and slippage.
    """

    without_fee_or_slippage: float
    with_fee: float
    without_fee: float
    fee: float


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class TradeResult:
    r"""The result of performing a trade.

    This includes granular information about the trade details,
    including the amount of fees collected and the total delta.
    Additionally, breakdowns for the updates that should be applied
    to the user and the market are computed.
    """

    user_result: AgentTradeResult
    market_result: MarketTradeResult
    breakdown: TradeBreakdown

    def __str__(self):
        output_string = (
            "TradeResult(\n"
            "\tuser_results(\n"
            f"\t\t{self.user_result.d_base=},\n"
            f"\t\t{self.user_result.d_bonds=},\n"
            "\t),\n"
            "\tmarket_result(\n"
            f"\t\t{self.market_result.d_base=},\n"
            f"\t\t{self.market_result.d_bonds=},\n"
            "\t),\n"
            "\tbreakdown(\n"
            f"\t\t{self.breakdown.without_fee_or_slippage=},\n"
            f"\t\t{self.breakdown.with_fee=},\n"
            f"\t\t{self.breakdown.without_fee=},\n"
            f"\t\t{self.breakdown.fee=},\n"
            "\t)\n"
            ")"
        )
        return output_string


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
    run_trade_number: list[int] = field(
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

    # Market
    target_liquidity: float = field(
        default=1e6, metadata=to_description("total size of the market pool (bonds + shares)")
    )
    target_volume: float = field(default=0.01, metadata=to_description("fraction of pool liquidity"))
    init_vault_age: float = field(default=0, metadata=to_description("fraction of a year since the vault was opened"))
    base_asset_price: float = field(default=2e3, metadata=to_description("market price"))
    # NOTE: We ignore the type error since the value will never be None after
    # initialization, and we don't want the value to be set to None downstream.
    vault_apr: list[float] = field(  # default is overridden in __post_init__
        default_factory=lambda: [-1],
        metadata=to_description("the underlying (variable) vault APR at each time step"),
    )
    init_share_price: float = field(  # default is overridden in __post_init__
        default=-1, metadata=to_description("initial market share price for the vault asset")  # type: ignore
    )

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
    # init_vault_age: float = field(default=0, metadata=to_description("initial vault age"))

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
        config_string = json.dumps(self.__dict__, sort_keys=True, indent=2, cls=CustomEncoder)
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
