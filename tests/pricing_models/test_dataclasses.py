"""
Useful dataclasses for testing a pricing model's calc_in_given_out method
"""

from __future__ import annotations
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
class TestResultCalcInGivenOutSuccessByModel:
    """Dataclass for calc_in_given_out test results by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: TestResultCalcInGivenOutSuccess
    hyperdrive: TestResultCalcInGivenOutSuccess


@dataclass
class TestCaseCalcInGivenOutFailure:
    """Dataclass for calc_in_given_out test cases"""

    out: Quantity
    market_state: MarketState
    trade_fee_percent: float
    redemption_fee_percent: float
    time_remaining: StretchedTime
    exception_type: Type[BaseException]

    __test__ = False  # pytest: don't test this class


@dataclass
class TestResultCalcInGivenOutFailureByModel:
    """Dataclass for calc_in_given_out test cases by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: TestCaseCalcInGivenOutFailure
    hyperdrive: TestCaseCalcInGivenOutFailure


@dataclass
class TestCaseCalcOutGivenInSuccess:
    """Dataclass for calc_out_given_in success test cases"""

    in_: Quantity
    market_state: MarketState
    fee_percent: float
    days_remaining: float
    time_stretch_apy: float

    __test__ = False  # pytest: don't test this class


@dataclass
class TestResultCalcOutGivenInSuccess:
    """Dataclass for calc_out_given_in test results"""

    without_fee_or_slippage: float
    without_fee: float
    fee: float
    with_fee: float

    __test__ = False  # pytest: don't test this class


@dataclass
class TestResultCalcOutGivenInSuccessByModel:
    """Dataclass for calc_out_given_in success test cases by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: TestResultCalcOutGivenInSuccess
    hyperdrive: TestResultCalcOutGivenInSuccess


@dataclass
class TestCaseCalcOutGivenInFailure:
    """Dataclass for calc_out_given_in failure test cases"""

    in_: Quantity
    market_state: MarketState
    trade_fee_percent: float
    redemption_fee_percent: float
    time_remaining: StretchedTime
    exception_type: Type[Exception] | tuple[Type[Exception], Type[Exception]]

    __test__ = False  # pytest: don't test this class


@dataclass
class TestCaseCalcOutGivenInFailureByModel:
    """Dataclass for calc_out_given_in failure test cases by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: TestCaseCalcOutGivenInFailure
    hyperdrive: TestCaseCalcOutGivenInFailure
