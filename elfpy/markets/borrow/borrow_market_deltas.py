"""Class for for storing the delta values for MarketState"""
from __future__ import annotations
from dataclasses import dataclass, field

import elfpy.types as types

from elfpy.markets.base import BaseMarketDeltas
from elfpy.math import FixedPoint


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class BorrowMarketDeltas(BaseMarketDeltas):
    r"""Specifies changes to values in the market"""

    d_borrow_shares: FixedPoint = FixedPoint("0.0")  # borrow is always in DAI
    d_collateral: types.Quantity = field(
        default_factory=lambda: types.Quantity(amount=FixedPoint("0.0"), unit=types.TokenType.PT)
    )
    d_borrow_outstanding: FixedPoint = FixedPoint("0.0")  # changes based on borrow_shares * borrow_share_price
    d_borrow_closed_interest: FixedPoint = FixedPoint("0.0")  # realized interest from closed borrows
    d_borrow_share_price: FixedPoint = FixedPoint("0.0")  # used only when time ticks and interest accrues
