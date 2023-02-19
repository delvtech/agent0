"""Useful dataclasses for testing a pricing model's calc_in_given_out method"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Type, Optional

from elfpy.types import MarketState, Quantity, StretchedTime


@dataclass
class CalcInGivenOutSuccessTestCase:
    """Dataclass for calc_in_given_out test cases"""

    out: Quantity
    market_state: MarketState
    days_remaining: float
    time_stretch_apy: float


@dataclass
class CalcInGivenOutSuccessTestResult:
    """Dataclass for calc_in_given_out test results"""

    without_fee_or_slippage: float
    without_fee: float
    fee: float
    with_fee: float


@dataclass
class CalcInGivenOutSuccessByModelTestResult:
    """Dataclass for calc_in_given_out test results by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: Optional[CalcInGivenOutSuccessTestResult] = None
    hyperdrive: Optional[CalcInGivenOutSuccessTestResult] = None


@dataclass
class CalcInGivenOutFailureTestCase:
    """Dataclass for calc_in_given_out test cases"""

    out: Quantity
    market_state: MarketState
    time_remaining: StretchedTime
    exception_type: Type[Exception] | tuple[Type[Exception], Type[Exception]]


@dataclass
class CalcInGivenOutFailureByModelTestResult:
    """Dataclass for calc_in_given_out test cases by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: CalcInGivenOutFailureTestCase
    hyperdrive: CalcInGivenOutFailureTestCase


@dataclass
class CalcOutGivenInSuccessTestCase:
    """Dataclass for calc_out_given_in success test cases"""

    in_: Quantity
    market_state: MarketState
    days_remaining: float
    time_stretch_apy: float


@dataclass
class CalcOutGivenInSuccessTestResult:
    """Dataclass for calc_out_given_in test results"""

    without_fee_or_slippage: float
    without_fee: float
    fee: float
    with_fee: float


@dataclass
class CalcOutGivenInSuccessByModelTestResult:
    """Dataclass for calc_out_given_in success test cases by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: CalcOutGivenInSuccessTestResult
    hyperdrive: CalcOutGivenInSuccessTestResult


@dataclass
class CalcOutGivenInFailureTestCase:
    """Dataclass for calc_out_given_in failure test cases"""

    in_: Quantity
    market_state: MarketState
    time_remaining: StretchedTime
    exception_type: Type[Exception] | tuple[Type[Exception], Type[Exception]]


@dataclass
class CalcOutGivenInFailureByModelTestCase:
    """Dataclass for calc_out_given_in failure test cases by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: CalcOutGivenInFailureTestCase
    hyperdrive: CalcOutGivenInFailureTestCase
