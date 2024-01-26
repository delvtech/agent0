"""Calculate the fixed interest rate."""

from decimal import ROUND_DOWN, ROUND_UP, Decimal, localcontext

import pandas as pd


def calc_fixed_rate(spot_price: pd.Series, position_duration: Decimal) -> pd.Series:
    """Calculates the fixed rate given trade data.

    Arguments
    ---------
    spot_price: pd.Series
        The spot price.
    position_duration: Decimal
        The position duration in seconds.

    Returns
    -------
    pd.Series
        The fixed interest rate.
    """
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
