"""Calculate the fixed interest rate."""
from __future__ import annotations

from decimal import ROUND_DOWN, ROUND_UP, Decimal, localcontext
from typing import overload

import pandas as pd
from fixedpointmath import FixedPoint

SECONDS_IN_YEAR = FixedPoint(365 * 24 * 60 * 60)  # 31_536_000


@overload
def calc_fixed_rate(spot_price: pd.Series, position_duration: Decimal) -> pd.Series:
    ...


@overload
def calc_fixed_rate(spot_price: FixedPoint | int, position_duration: FixedPoint | int) -> FixedPoint:
    ...


def calc_fixed_rate(
    spot_price: pd.Series | FixedPoint | int, position_duration: Decimal | FixedPoint | int
) -> pd.Series | FixedPoint:
    """Calculate the fixed rate given trade data in either (pd.Series, Decimal) or (FixedPoint | int, FixedPoint | int) format."""
    if isinstance(spot_price, pd.Series) and isinstance(position_duration, Decimal):
        return calc_fixed_rate_decimal(spot_price, position_duration)
    if isinstance(spot_price, FixedPoint) and isinstance(position_duration, FixedPoint | int):
        return calc_fixed_rate_fp(spot_price, position_duration)
    raise TypeError(
        "spot_price and position_duration must be either (pd.Series, Decimal) or (FixedPoint | int, FixedPoint | int)"
    )


def calc_fixed_rate_decimal(spot_price: pd.Series, position_duration: Decimal) -> pd.Series:
    """Calculate the fixed rate given trade data in Decimal format."""
    # Position duration (in seconds) in terms of fraction of year
    # This div should round up
    # This replicates div up in fixed point
    with localcontext() as ctx:
        ctx.prec = 18
        ctx.rounding = ROUND_UP
        annualized_time = position_duration / Decimal(60 * 60 * 24 * 365)

    # Pandas is smart enough to be able to broadcast with internal Decimal types at runtime
    # We keep things in 18 precision here
    with localcontext() as ctx:
        ctx.prec = 18
        ctx.rounding = ROUND_DOWN
        fixed_rate = (1 - spot_price) / (spot_price * annualized_time)  # type: ignore
    return fixed_rate


def calc_fixed_rate_fp(spot_price: FixedPoint | int, position_duration: FixedPoint | int) -> FixedPoint:
    """Calculate the fixed rate given data in FixedPoint format."""
    return (1 - spot_price) / (spot_price * (position_duration / SECONDS_IN_YEAR))
