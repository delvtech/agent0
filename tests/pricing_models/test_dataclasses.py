"""
Useful dataclasses for testing a pricing model's calc_in_given_out method
"""

from dataclasses import dataclass
from typing import Type
from elfpy.types import MarketState, Quantity, StretchedTime


@dataclass
class TestCaseCalcInGivenOutSuccess:
    """Dataclass for calc_in_given_out test cases"""

    out: Quantity
    market_state: MarketState
    fee_percent: float
    days_remaining: float
    time_stretch_apy: float

    __test__ = False  # pytest: don't test this class


@dataclass
class TestResultCalcInGivenOutSuccess:
    """Dataclass for calc_in_given_out test results"""

    without_fee_or_slippage: float
    without_fee: float
    fee: float
    with_fee: float

    __test__ = False  # pytest: don't test this class


@dataclass
class TestCaseCalcInGivenOutFailure:
    """Dataclass for calc_in_given_out test cases"""

    out: Quantity
    market_state: MarketState
    fee_percent: float
    time_remaining: StretchedTime
    exception_type: Type[BaseException]

    __test__ = False  # pytest: don't test this class
