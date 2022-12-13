from dataclasses import dataclass
from typing import NamedTuple
from typing import Literal

import elfpy.utils.time as time_utils


TokenType = Literal["pt", "base"]


class Quantity(NamedTuple):
    """An amount with a unit"""

    amount: float
    unit: TokenType


class StretchedTime:
    """A stretched time value with the time stretch"""

    def __init__(self, days_remaining: float, time_stretch: float):
        self._days_remaining = days_remaining
        self._time_stretch = time_stretch
        self._stretched_time = time_utils.days_to_time_remaining(self._days_remaining, self._time_stretch)

    @property
    def days_remaining(self):
        return self._days_remaining

    @property
    def normalized_days_remaining(self):
        return time_utils.norm_days(self._days_remaining)

    @property
    def stretched_time(self):
        return self._stretched_time

    @property
    def time_stretch(self):
        return self._time_stretch


# TODO: We can add class methods for computing common quantities like bond_reserves + total_supply
@dataclass
class MarketState:
    """The state of an AMM"""

    share_reserves: float
    bond_reserves: float
    share_price: float = 1.0
    init_share_price: float = 1.0


class TradeResult(NamedTuple):
    """
    Result from a calc_out_given_in or calc_in_given_out.  The values are the amount of asset required
    for the trade, either in or out.  Fee is the amount of fee collected, if any.
    """

    without_fee_or_slippage: float
    with_fee: float
    without_fee: float
    fee: float
