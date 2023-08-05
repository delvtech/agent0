"""Calculate the fixed interest rate."""
from decimal import Decimal

import numpy as np
from chainsync.dashboard.extract_data_logs import calculate_spot_price


def calc_fixed_rate(trade_data, config_data):
    """Calculates the fixed rate given trade data."""
    trade_data["rate"] = np.nan
    annualized_time = config_data["positionDuration"] / Decimal(60 * 60 * 24 * 365)
    spot_price = calculate_spot_price(
        trade_data["share_reserves"],
        trade_data["bond_reserves"],
        config_data["initialSharePrice"],
        config_data["invTimeStretch"],
    )
    fixed_rate = (Decimal(1) - spot_price) / (spot_price * annualized_time)
    x_data = trade_data["timestamp"]
    y_data = fixed_rate
    return (x_data, y_data)
