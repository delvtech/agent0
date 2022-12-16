"""A set of common types used throughtout the simulation codebase."""

from dataclasses import dataclass
from enum import Enum

from elfpy.utils.outputs import float_to_string
import elfpy.utils.time as time_utils


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
    def normalized_days(self):
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
            f" {self.normalized_days=};"
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
    d_share_buffer: float = 0
    d_bond_buffer: float = 0
    d_lp_reserves: float = 0

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


# TODO: We can add class methods for computing common quantities like bond_reserves + total_supply
@dataclass
class MarketState:
    """The state of an AMM"""

    # trading reserves
    share_reserves: float = 0.0
    bond_reserves: float = 0.0

    # trading buffers
    share_buffer: float = 0.0  # TODO: This shouldn't be a share buffer. It needs to be a base buffer.
    bond_buffer: float = 0.0

    # lp reserves
    lp_reserves: float = 0.0

    # share price
    share_price: float = 1.0
    init_share_price: float = 1.0

    def apply_delta(
        self,
        # TODO: This should be moved into the types file and should get better
        # names ("base_asset" => "base_reserves" and "token_asset" => bond_reserves").
        delta: MarketDeltas,
    ):
        """Applies a delta to the market state."""
        self.share_reserves += delta.d_base_asset / self.share_price
        self.bond_reserves += delta.d_token_asset
        self.share_buffer += delta.d_share_buffer
        self.bond_buffer += delta.d_bond_buffer
        self.lp_reserves += delta.d_lp_reserves

    def __str__(self):
        out_str = (
            "Trading reserves:\n"
            f"\t{self.share_reserves=}\n"
            f"\t{self.bond_reserves=}\n"
            "Trading buffers:\n"
            f"\t{self.share_buffer=}\n"
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
