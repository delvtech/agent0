"""Market simulators store state information when interfacing AMM pricing models with users."""
from __future__ import annotations  # types will be strings by default in 3.11

from enum import Enum
from dataclasses import dataclass

import elfpy.types as types
import elfpy.markets.yieldspace as yieldspace_market


# TODO: for now...
# pylint: disable=duplicate-code


class MarketActionType(Enum):
    r"""The descriptor of an action in a market"""

    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"

    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketDeltas(yieldspace_market.MarketDeltas):
    r"""Specifies changes to values in the market"""


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class MarketTradeResult(yieldspace_market.MarketTradeResult):
    r"""The result to a market of performing a trade"""


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass
class MarketState(yieldspace_market.MarketState):
    r"""The state of an AMM

    Attributes
    ----------
    lp_total_supply: float
        Amount of lp tokens
    share_reserves: float
        Quantity of shares stored in the market
    bond_reserves: float
        Quantity of bonds stored in the market
    base_buffer: float
        Base amount set aside to account for open longs
    bond_buffer: float
        Bond amount set aside to account for open shorts
    variable_apr: float
        apr of underlying yield-bearing source
    share_price: float
        ratio of value of base & shares that are stored in the underlying vault,
        i.e. share_price = base_value / share_value
    init_share_price: float
        share price at pool initialization
    trade_fee_percent : float
        The percentage of the difference between the amount paid without
        slippage and the amount received that will be added to the input
        as a fee.
    redemption_fee_percent : float
        A flat fee applied to the output.  Not used in this equation for Yieldspace.
    """


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class MarketAction(yieldspace_market.MarketAction):
    r"""Market action specification"""


class Market(yieldspace_market.Market[MarketState, MarketDeltas]):
    r"""Market state simulator

    Holds state variables for market simulation and executes trades.
    The Market class executes trades by updating market variables according to the given pricing model.
    It also has some helper variables for assessing pricing model values given market conditions.
    """

    @property
    def name(self) -> types.MarketType:
        return types.MarketType.HYPERDRIVE
