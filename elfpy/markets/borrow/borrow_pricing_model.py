"""Pricing model for the borrow market"""
from __future__ import annotations

import elfpy.types as types

from elfpy.markets.base import BasePricingModel
from elfpy.math import FixedPoint


class BorrowPricingModel(BasePricingModel):
    """stores calculation functions use for the borrow market"""

    def value_collateral(
        self,
        loan_to_value_ratio: dict[types.TokenType, FixedPoint],
        collateral: types.Quantity,
        spot_price: FixedPoint | None = None,
    ):
        """Values collateral and returns how much the agent can borrow against it"""
        collateral_value_in_base = collateral.amount  # if collateral is BASE
        if collateral.unit == types.TokenType.PT:
            collateral_value_in_base = collateral.amount * (spot_price or FixedPoint("1.0"))
        borrow_amount_in_base = collateral_value_in_base * loan_to_value_ratio[collateral.unit]  # type: ignore
        return collateral_value_in_base, borrow_amount_in_base
