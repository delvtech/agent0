"""A set of common types used throughtout the simulation codebase"""

from __future__ import annotations  # types will be strings by default in 3.11
from typing import TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

import elfpy.utils.time as time_utils

if TYPE_CHECKING:
    from elfpy.agent import Agent
    from elfpy.markets import Market


def to_description(description: str) -> dict[str, str]:
    r"""A dataclass helper that constructs metadata containing a description."""
    return {"description": description}


# This is the minimum allowed value to be passed into calculations to avoid
# problems with sign flips that occur when the floating point range is exceeded.
WEI = 1e-18  # smallest denomination of ether

# The maximum allowed difference between the base reserves and bond reserves.
# This value was calculated using trial and error and is close to the maximum
# difference between the reserves that will not result in a sign flip when a
# small trade is put on.
MAX_RESERVES_DIFFERENCE = 2e10


class TokenType(Enum):
    r"""A type of token"""

    BASE = "base"
    PT = "pt"


class MarketActionType(Enum):
    r"""The descriptor of an action in a market"""

    # TODO: Add this in INITIALIZE_MARKET = "initialize_market"

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


class StretchedTime:
    r"""A stretched time value with the time stretch"""

    # TODO: Improve this constructor so that StretchedTime can be constructed
    # from years.
    def __init__(self, days: float, time_stretch: float, normalizing_constant: float = 365):
        self._days = days
        self._time_stretch = time_stretch
        self._stretched_time = time_utils.days_to_time_remaining(self._days, self._time_stretch)
        self.normalizing_constant = normalizing_constant

    @property
    def days(self):
        r"""Format time as days"""
        return self._days

    @property
    def normalized_time(self):
        r"""Format time as normalized days"""
        return time_utils.norm_days(
            self._days,
            self.normalizing_constant,
        )

    @property
    def stretched_time(self):
        r"""Format time as stretched time"""
        return self._stretched_time

    @property
    def time_stretch(self):
        r"""The time stretch constant"""
        return self._time_stretch

    def __str__(self):
        output_string = (
            "Time components:"
            f" {self.days=};"
            f" {self.normalized_time=};"
            f" {self.stretched_time=};"
            f" {self.time_stretch=};"
        )
        return output_string


@dataclass
class MarketAction:
    r"""Market action specification"""

    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    trade_amount: float
    # TODO: pass in the entire wallet instead of wallet_address and the open_share_price
    # wallet_address is always set automatically by the basic agent class
    wallet_address: int
    # the share price when a short was created
    open_share_price: float = 1
    # mint time is set only for trades that act on existing positions (close long or close short)
    mint_time: float = 0

    def __str__(self):
        r"""Return a description of the Action"""
        output_string = f"AGENT ACTION:\nagent #{self.wallet_address}"
        for key, value in self.__dict__.items():
            if key == "action_type":
                output_string += f" execute {value}()"
            elif key in ["trade_amount", "mint_time"]:
                output_string += f" {key}: {value}"
            elif key not in ["wallet_address", "agent"]:
                output_string += f" {key}: {value}"
        return output_string


@dataclass(frozen=False)
class MarketDeltas:
    r"""Specifies changes to values in the market"""

    # TODO: Create our own dataclass decorator that is always mutable and includes dict set/get syntax
    # pylint: disable=duplicate-code
    # pylint: disable=too-many-instance-attributes

    # TODO: Use better naming for these values:
    # - "d_base_asset" => "d_share_reserves" TODO: Is there some reason this is base instead of shares?
    # - "d_token_asset" => "d_bond_reserves"
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


@dataclass
class MarketState:
    r"""The state of an AMM

    Implements a class for all that that an AMM smart contract would hold or would have access to
    For example, reserve numbers are local state variables of the AMM.  The vault_apr will most
    likely be accessible through the AMM as well.

    Attributes
    ----------
    share_reserves: float
        TODO: fill this in
    bond_reserves: float
        TODO: fill this in
    base_buffer: float
        TODO: fill this in
    bond_buffer: float
        TODO: fill this in
    lp_reserves: float
        TODO: fill this in
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


@dataclass
class AgentTradeResult:
    r"""The result to a user of performing a trade"""

    d_base: float
    d_bonds: float


@dataclass
class MarketTradeResult:
    r"""The result to a market of performing a trade"""

    d_base: float
    d_bonds: float


@dataclass
class TradeBreakdown:
    r"""A granular breakdown of a trade.

    This includes information relating to fees and slippage.
    """

    without_fee_or_slippage: float
    with_fee: float
    without_fee: float
    fee: float


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


@dataclass()
class RandomSimulationVariables:
    r"""Random variables to be used during simulation setup & execution"""

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    target_liquidity: float = field(metadata=to_description("total size of the market pool (bonds + shares)"))
    target_pool_apr: float = field(metadata=to_description("desired fixed apr for as a decimal"))
    trade_fee_percent: float = field(metadata=to_description("LP fee percent to charge for trades"))
    redemption_fee_percent: float = field(metadata=to_description("LP fee percent to charge for redemption"))
    vault_apr: list = field(metadata=to_description("yield bearing source APR"))
    init_vault_age: float = field(metadata=to_description("fraction of a year since the vault was opened"))
    # NOTE: We ignore the type error since the value will never be None after
    # initialization, and we don't want the value to be set to None downstream.
    init_share_price: float = field(
        default=None, metadata=to_description("initial market share price for the vault asset")  # type: ignore
    )

    def __post_init__(self):
        r"""init_share_price is a function of other random variables"""
        if self.init_share_price is None:
            self.init_share_price = (1 + self.vault_apr[0]) ** self.init_vault_age


@dataclass
class SimulationState:
    r"""Simulator state, updated after each trade"""

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    model_name: list = field(
        default_factory=list, metadata=to_description("the name of the pricing model that is used in simulation")
    )
    run_number: list = field(default_factory=list, metadata=to_description("simulation index"))
    simulation_start_time: list = field(
        default_factory=list, metadata=to_description("start datetime for a given simulation")
    )
    day: list = field(default_factory=list, metadata=to_description("day index in a given simulation"))
    block_number: list = field(
        default_factory=list, metadata=to_description(" integer, block index in a given simulation")
    )
    daily_block_number: list = field(
        default_factory=list, metadata=to_description(" integer, block index in a given day")
    )
    block_timestamp: list = field(
        default_factory=list, metadata=to_description(" datetime of a given block's creation")
    )
    current_market_datetime: list = field(
        default_factory=list, metadata=to_description(" float, current market time as a datetime")
    )
    current_market_time: list = field(
        default_factory=list, metadata=to_description(" float, current market time in years")
    )
    run_trade_number: list = field(
        default_factory=list, metadata=to_description(" integer, trade number in a given simulation")
    )
    market_step_size: list = field(
        default_factory=list, metadata=to_description(" minimum time discretization for market time step")
    )
    position_duration: list = field(
        default_factory=list, metadata=to_description(" time lapse between token mint and expiry as a yearfrac")
    )
    target_liquidity: list = field(
        default_factory=list, metadata=to_description("amount of liquidity the market should stop with")
    )
    trade_fee_percent: list = field(
        default_factory=list, metadata=to_description("the percentage of trade outputs to be collected as fees")
    )
    redemption_fee_percent: list = field(
        default_factory=list, metadata=to_description("the percentage of redemption outputs to be collected as fees")
    )
    floor_fee: list = field(default_factory=list, metadata=to_description(" minimum fee we take"))
    init_vault_age: list = field(default_factory=list, metadata=to_description("the age of the underlying vault"))
    base_asset_price: list = field(default_factory=list, metadata=to_description("the market price of the shares"))
    pool_apr: list = field(default_factory=list, metadata=to_description("apr of the AMM pool"))
    num_trading_days: list = field(default_factory=list, metadata=to_description(" number of days in a simulation"))
    num_blocks_per_day: list = field(
        default_factory=list, metadata=to_description(" number of blocks in a day, simulates time between blocks")
    )
    spot_price: list = field(default_factory=list, metadata=to_description("price of shares"))

    def update_market_state(self, market_state: MarketState) -> None:
        r"""Update each entry in the SimulationState's copy for the market state
        by appending to the list for each key, or creating a new key.

        Parameters
        ----------
        market_state: MarketState
            The state variable for the Market class
        """
        for key, val in market_state.__dict__.items():
            if hasattr(self, key):
                attribute_state = getattr(self, key)
                attribute_state.append(val)
                setattr(self, key, attribute_state)
            else:
                setattr(self, key, [val])

    def update_agent_wallet(self, agent: Agent, market: Market) -> None:
        r"""Update each entry in the SimulationState's copy for the agent wallet state
        by appending to the list for each key, or creating a new key.

        Parameters
        ----------
        agent: Agent
            An instantiated Agent object
        """
        for key, value in agent.wallet.get_state(market).items():
            if hasattr(self, key):
                key_list = getattr(self, key)
                key_list.append(value)
                setattr(self, key, key_list)
            else:
                setattr(self, key, [value])

    def __getitem__(self, key):
        r"""Get object attribute referenced by `key`"""
        return getattr(self, key)

    def __setitem__(self, key, value):
        r"""Set object attribute referenced by `key` to `value`"""
        setattr(self, key, value)
