"""Useful dataclasses for testing a pricing model's calc_in_given_out method"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Type, Optional

from pytest import skip

from elfpy.types import MarketState, Quantity, StretchedTime

skip(msg="These are dataclasses used for tests, not tests themselves", allow_module_level=True)


@dataclass
class TestCaseCalcInGivenOutSuccess:
    """Dataclass for calc_in_given_out test cases"""

    out: Quantity
    market_state: MarketState
    days_remaining: float
    time_stretch_apy: float


@dataclass
class TestResultCalcInGivenOutSuccess:
    """Dataclass for calc_in_given_out test results"""

    without_fee_or_slippage: float
    without_fee: float
    fee: float
    with_fee: float


@dataclass
class TestResultCalcInGivenOutSuccessByModel:
    """Dataclass for calc_in_given_out test results by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: Optional[TestResultCalcInGivenOutSuccess] = None
    hyperdrive: Optional[TestResultCalcInGivenOutSuccess] = None


@dataclass
class TestCaseCalcInGivenOutFailure:
    """Dataclass for calc_in_given_out test cases"""

    out: Quantity
    market_state: MarketState
    time_remaining: StretchedTime
    exception_type: Type[Exception] | tuple[Type[Exception], Type[Exception]]


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
    days_remaining: float
    time_stretch_apy: float


@dataclass
class TestResultCalcOutGivenInSuccess:
    """Dataclass for calc_out_given_in test results"""

    without_fee_or_slippage: float
    without_fee: float
    fee: float
    with_fee: float


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
    time_remaining: StretchedTime
    exception_type: Type[Exception] | tuple[Type[Exception], Type[Exception]]


@dataclass
class TestCaseCalcOutGivenInFailureByModel:
    """Dataclass for calc_out_given_in failure test cases by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: TestCaseCalcOutGivenInFailure
    hyperdrive: TestCaseCalcOutGivenInFailure
