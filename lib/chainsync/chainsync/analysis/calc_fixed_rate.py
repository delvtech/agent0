"""Calculate the fixed interest rate."""
from decimal import Decimal

import pandas as pd


def calc_fixed_rate(spot_price: pd.Series, position_duration: Decimal):
    """Calculates the fixed rate given trade data."""
    # Position duration (in seconds) in terms of fraction of year
    annualized_time = position_duration / Decimal(60 * 60 * 24 * 365)
    # Pandas is smart enough to be able to broadcast with internal Decimal types at runtime
    fixed_rate = (1 - spot_price) / (spot_price * annualized_time)  # type: ignore
    return fixed_rate
