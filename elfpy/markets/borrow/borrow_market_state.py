"""Class that holds the state for the borrow market"""
from __future__ import annotations
from dataclasses import dataclass, field

import elfpy.types as types

from elfpy.markets.base.base_market import BaseMarketState
from elfpy.markets.borrow.borrow_market_deltas import BorrowMarketDeltas
from elfpy.math import FixedPoint


@types.freezable(frozen=False, no_new_attribs=False)
@dataclass
class BorrowMarketState(BaseMarketState):
    r"""The state of an AMM
    Implements a class for all that an AMM smart contract would hold or would have access to
    For example, reserve numbers are local state variables of the AMM.  The borrow_rate will most
    likely be accessible through the AMM as well.
    Attributes
    ----------
    loan_to_value_ratio: FixedPoint
        The maximum loan to value ratio a collateral can have before liquidations occur.
    borrow_shares: FixedPoint
        Accounting units for borrow assets that has been lent out by the market, allows tracking of interest
    collateral: dict[TokenType, FixedPoint]
        Amount of collateral that has been deposited into the market
    borrow_outstanding: FixedPoint
        The amount of borrowed asset that has been lent out by the market, without accounting for interest
    borrow_share_price: FixedPoint
        The "share price" of the borrowed asset tracks the cumulative amount owed over time, indexed to 1 at the start
    borrow_closed_interest: FixedPoint
        The interest that has been collected from closed borrows, to capture realized profit
    collateral_spot_price: FixedPoint
        The spot price of the collateral asset, to allow updating valuation across time
    lending_rate: FixedPoint
        The rate a user receives when lending out assets
    spread_ratio: FixedPoint
        The ratio of the borrow rate to the lending rate
    """
    # dataclasses can have many attributes
    # pylint: disable=too-many-instance-attributes

    # TODO: Should we be tracking the last time the dsr changed to evaluate the payout amount correctly?
    # borrow ratios
    loan_to_value_ratio: dict[types.TokenType, FixedPoint] = field(
        default_factory=lambda: {token_type: FixedPoint("0.97") for token_type in types.TokenType}
    )
    # trading reserves
    borrow_shares: FixedPoint = FixedPoint("0.0")  # allows tracking the increasing value of loans over time
    collateral: dict[types.TokenType, FixedPoint] = field(default_factory=dict)
    borrow_outstanding: FixedPoint = FixedPoint("0.0")  # sum of Dai that went out the door
    borrow_closed_interest: FixedPoint = FixedPoint("0.0")  # interested collected from closed borrows
    # share prices used to track amounts owed
    borrow_share_price: FixedPoint = FixedPoint("1.0")
    init_borrow_share_price: FixedPoint = field(default=borrow_share_price)  # allow not setting init_share_price
    # number of TokenA you get for TokenB
    collateral_spot_price: dict[types.TokenType, FixedPoint] = field(default_factory=dict)
    # borrow and lending rates
    lending_rate: FixedPoint = FixedPoint("0.01")  # 1% per year
    # borrow rate is lending_rate * spread_ratio
    spread_ratio: FixedPoint = FixedPoint("1.25")

    @property
    def borrow_amount(self) -> FixedPoint:
        """The amount of borrowed asset in the market"""
        return self.borrow_shares * self.borrow_share_price

    @property
    def deposit_amount(self) -> dict[types.TokenType, FixedPoint]:
        """The amount of deposited asset in the market"""
        return {key: value * self.collateral_spot_price[key] for key, value in self.collateral.items()}

    def apply_delta(self, delta: BorrowMarketDeltas) -> None:
        r"""Applies a delta to the market state."""
        self.borrow_shares += delta.d_borrow_shares
        collateral_unit = delta.d_collateral.unit
        if collateral_unit not in self.collateral:  # key doesn't exist
            self.collateral[collateral_unit] = delta.d_collateral.amount
        else:  # key exists
            self.collateral[collateral_unit] += delta.d_collateral.amount

    def copy(self) -> BorrowMarketState:
        """Returns a new copy of self"""
        return BorrowMarketState(**self.__dict__)

    def check_valid_market_state(self, dictionary: dict | None = None) -> None:
        """Test that all market state variables are greater than zero"""
        if dictionary is None:
            self.check_valid_market_state(self.__dict__)
        else:
            for key, value in dictionary.items():
                if isinstance(value, FixedPoint):
                    assert value >= FixedPoint(0), f"{key} attribute with {value=} must be >= 0."
                elif isinstance(value, dict):
                    self.check_valid_market_state(value)
                else:
                    pass  # noop; frozen, etc
