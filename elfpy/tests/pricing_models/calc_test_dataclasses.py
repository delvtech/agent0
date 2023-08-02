"""Useful dataclasses for testing a pricing model's calc_in_given_out method"""
from __future__ import annotations

import builtins
from dataclasses import dataclass
from typing import Optional, Type

from fixedpointmath import FixedPoint

import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market
import elfpy.time as time
import elfpy.types as types


@dataclass
class CalcInGivenOutSuccessTestCase:
    """Dataclass for calc_in_given_out test cases"""

    out: types.Quantity
    market_state: hyperdrive_market.HyperdriveMarketState
    days_remaining: FixedPoint
    time_stretch_apy: FixedPoint


@dataclass
class CalcInGivenOutSuccessTestResult:
    """Dataclass for calc_in_given_out test results"""

    without_fee_or_slippage: FixedPoint
    without_fee: FixedPoint
    fee: FixedPoint
    with_fee: FixedPoint


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

    out: types.Quantity
    market_state: hyperdrive_market.HyperdriveMarketState
    time_remaining: time.StretchedTime
    exception_type: Type[builtins.BaseException] | tuple[Type[builtins.BaseException], Type[builtins.BaseException]]


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

    in_: types.Quantity
    market_state: hyperdrive_market.HyperdriveMarketState
    days_remaining: FixedPoint
    time_stretch_apy: FixedPoint


@dataclass
class CalcOutGivenInSuccessTestResult:
    """Dataclass for calc_out_given_in test results"""

    without_fee_or_slippage: FixedPoint
    without_fee: FixedPoint
    fee: FixedPoint
    with_fee: FixedPoint


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

    in_: types.Quantity
    market_state: hyperdrive_market.HyperdriveMarketState
    time_remaining: time.StretchedTime
    exception_type: Type[builtins.BaseException] | tuple[Type[builtins.BaseException], Type[builtins.BaseException]]


@dataclass
class CalcOutGivenInFailureByModelTestCase:
    """Dataclass for calc_out_given_in failure test cases by pricing_model"""

    def __getitem__(self, key):
        """Get object attribute referenced by `key`"""
        return getattr(self, key)

    yieldspace: CalcOutGivenInFailureTestCase
    hyperdrive: CalcOutGivenInFailureTestCase
