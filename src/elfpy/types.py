"""A set of common types used throughtout the simulation codebase."""

from __future__ import annotations  # types will be strings by default in 3.11
from typing import TYPE_CHECKING
from dataclasses import dataclass, field
from enum import Enum

from elfpy.utils.outputs import float_to_string
import elfpy.utils.time as time_utils

if TYPE_CHECKING:
    from elfpy.agent import Agent
    from typing import Any


class TokenType(Enum):
    """A type of token"""

    BASE = "base"
    PT = "pt"


class MarketActionType(Enum):
    """The descriptor of an action in a market"""

    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"

    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"


@dataclass
class Quantity:
    """An amount with a unit"""

    amount: float
    unit: TokenType


class StretchedTime:
    """A stretched time value with the time stretch"""

    # TODO: Improve this constructor so that StretchedTime can be constructed
    # from yearfracs.
    def __init__(self, days: float, time_stretch: float):
        self._days = days
        self._time_stretch = time_stretch
        self._stretched_time = time_utils.days_to_time_remaining(self._days, self._time_stretch)

    @property
    def days(self):
        """Format time as days."""
        return self._days

    @property
    def normalized_time(self):
        """Format time as normalized days."""
        return time_utils.norm_days(self._days)

    @property
    def stretched_time(self):
        """Format time as stretched time."""
        return self._stretched_time

    @property
    def time_stretch(self):
        """The time stretch constant."""
        return self._time_stretch

    def __str__(self):
        out_str = (
            "Time components:"
            f" {self.days=};"
            f" {self.normalized_time=};"
            f" {self.stretched_time=};"
            f" {self.time_stretch=};"
        )
        return out_str


@dataclass
class MarketAction:
    """market action specification"""

    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    trade_amount: float
    # wallet_address is always set automatically by the basic agent class
    wallet_address: int
    # mint time is set only for trades that act on existing positions (close long or close short)
    mint_time: float = 0

    def __str__(self):
        """Return a description of the Action"""
        output_string = f"AGENT ACTION:\nagent #{self.wallet_address}"
        for key, value in self.__dict__.items():
            if key == "action_type":
                output_string += f" execute {value}()"
            elif key in ["trade_amount", "mint_time"]:
                output_string += f" {key}: {float_to_string(value)}"
            elif key not in ["wallet_address", "agent"]:
                output_string += f" {key}: {float_to_string(value)}"
        return output_string


@dataclass(frozen=False)
class MarketDeltas:
    """Specifies changes to values in the market"""

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
        getattr(self, key)

    def __setitem__(self, key, value):
        setattr(self, key, value)

    def __str__(self):
        output_string = ""
        for key, value in vars(self).items():
            if value:  #  check if object exists
                if value != 0:
                    output_string += f" {key}: "
                    if isinstance(value, float):
                        output_string += f"{float_to_string(value)}"
                    elif isinstance(value, list):
                        output_string += "[" + ", ".join([float_to_string(x) for x in value]) + "]"
                    elif isinstance(value, dict):
                        output_string += "{" + ", ".join([f"{k}: {float_to_string(v)}" for k, v in value.items()]) + "}"
                    else:
                        output_string += f"{value}"
        return output_string


@dataclass
class MarketState:
    """The state of an AMM
    TODO: We can add class methods for computing common quantities like bond_reserves + total_supply
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

    def apply_delta(self, delta: MarketDeltas) -> None:
        """Applies a delta to the market state."""
        self.share_reserves += delta.d_base_asset / self.share_price
        self.bond_reserves += delta.d_token_asset
        self.base_buffer += delta.d_base_buffer
        self.bond_buffer += delta.d_bond_buffer
        self.lp_reserves += delta.d_lp_reserves
        self.share_price += delta.d_share_price

    def __str__(self):
        out_str = (
            "Trading reserves:\n"
            f"\t{self.share_reserves=}\n"
            f"\t{self.bond_reserves=}\n"
            "Trading buffers:\n"
            f"\t{self.base_buffer=}\n"
            f"\t{self.bond_buffer=}\n"
            "LP reserves:\n"
            f"\t{self.lp_reserves=}\n"
            "Share price:\n"
            f"\t{self.share_price=}\n"
            f"\t{self.init_share_price=}"
        )
        return out_str


@dataclass
class UserTradeResult:
    """The result to a user of performing a trade."""

    d_base: float
    d_bonds: float


@dataclass
class MarketTradeResult:
    """The result to a market of performing a trade."""

    d_base: float
    d_bonds: float


@dataclass
class TradeBreakdown:
    """
    A granular breakdown of a trade. This includes information relating to fees
    and slippage.
    """

    without_fee_or_slippage: float
    with_fee: float
    without_fee: float
    fee: float


@dataclass
class TradeResult:
    """
    The result of performing a trade. This includes granular information about
    the trade details including the amount of fees collected and the total
    delta. Additionally, breakdowns for the updates that should be applied to
    the user and the market are computed.
    """

    user_result: UserTradeResult
    market_result: MarketTradeResult
    breakdown: TradeBreakdown


@dataclass()
class RandomSimulationVariables:
    """Random variables to be used during simulation setup & execution"""

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    target_liquidity: float = field(metadata="total size of the market pool (bonds + shares)")
    target_pool_apr: float = field(metadata="desired fixed apr for as a decimal")
    fee_percent: float = field(metadata="percent to charge for LPer fees")
    vault_apr: list = field(metadata="yield bearing source APR")
    init_vault_age: float = field(metadata="fraction of a year since the vault was opened")
    init_share_price: float = field(default=None, metadata="initial market share price for the vault asset")

    def __post_init__(self):
        """init_share_price is a function of other random variables"""
        if self.init_share_price is None:
            self.init_share_price = (1 + self.vault_apr[0]) ** self.init_vault_age


@dataclass
class SimulationState:
    """Simulator state, updated after each trade"""

    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes
    model_name: list = field(
        default_factory=list, metadata={"hint": "the name of the pricing model that is used in simulation"}
    )
    run_number: list = field(default_factory=list, metadata={"hint": "simulation index"})
    simulation_start_time: list = field(
        default_factory=list, metadata={"hint": "start datetime for a given simulation"}
    )
    day: list = field(default_factory=list, metadata={"hint": "day index in a given simulation"})
    block_number: list = field(default_factory=list, metadata={"hint": " integer, block index in a given simulation"})
    daily_block_number: list = field(default_factory=list, metadata={"hint": " integer, block index in a given day"})
    block_timestamp: list = field(default_factory=list, metadata={"hint": " datetime of a given block's creation"})
    current_market_datetime: list = field(
        default_factory=list, metadata={"hint": " float, current market time as a datetime"}
    )
    current_market_yearfrac: list = field(
        default_factory=list, metadata={"hint": " float, current market time as a yearfrac"}
    )
    run_trade_number: list = field(
        default_factory=list, metadata={"hint": " integer, trade number in a given simulation"}
    )
    market_step_size: list = field(
        default_factory=list, metadata={"hint": " minimum time discretization for market time step"}
    )
    position_duration: list = field(
        default_factory=list, metadata={"hint": " time lapse between token mint and expiry as a yearfrac"}
    )
    target_liquidity: list = field(
        default_factory=list, metadata={"hint": "amount of liquidity the market should stop with"}
    )
    fee_percent: list = field(
        default_factory=list, metadata={"hint": "the percentage of trade outputs to be collected as fees"}
    )
    floor_fee: list = field(default_factory=list, metadata={"hint": " minimum fee we take"})
    init_vault_age: list = field(default_factory=list, metadata={"hint": "the age of the underlying vault"})
    base_asset_price: list = field(default_factory=list, metadata={"hint": "the market price of the shares"})
    pool_apr: list = field(default_factory=list, metadata={"hint": "apr of the AMM pool"})
    num_trading_days: list = field(default_factory=list, metadata={"hint": " number of days in a simulation"})
    num_blocks_per_day: list = field(
        default_factory=list, metadata={"hint": " number of blocks in a day, simulates time between blocks"}
    )
    spot_price: list = field(default_factory=list, metadata={"hint": "price of shares"})

    def update_market_state(self, market_state: MarketState) -> None:
        """Update each entry in the SimulationState's copy for the market state
        by appending to the list for each key, or creating a new key.

        Arguments
        ---------
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

    def update_agent_wallet(self, log_index: int, agent: Agent) -> None:
        """Update each entry in the SimulationState's copy for the agent wallet state
        by appending to the list for each key, or creating a new key.

        Arguments
        ---------
        log_index : int
            Some index indicating the log entry, typically the simulation run_trade_number
        agent: Agent
            An instantiated Agent object
        """
        d_state = [log_index] + list(agent.wallet.state)
        if hasattr(self, f"agent_{agent.wallet.address}"):
            agent_state = getattr(self, f"agent_{agent.wallet.address}")
            agent_state.append(d_state)
            setattr(self, f"agent_{agent.wallet.address}", agent_state)
        else:
            setattr(self, f"agent_{agent.wallet.address}", [d_state])

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    def __setitem__(self, key, value):
        """Set object attribute referenced by `key` to `value`"""
        setattr(self, key, value)
