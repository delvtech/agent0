"""Calculate OHLCV values for Hyperdrive trading."""
from __future__ import annotations

import pandas as pd

from .calc_spot_price import calculate_spot_price


def calc_ohlcv(trade_data, config_data, freq="D"):
    """
    freq var: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
    """
    spot_prices = (
        calculate_spot_price(
            trade_data["share_reserves"],
            trade_data["bond_reserves"],
            config_data["initialSharePrice"],
            config_data["invTimeStretch"],
        )
        .to_frame()
        .astype(float)
    )

    spot_prices.columns = ["spot_price"]
    value = trade_data["value"]

    spot_prices["value"] = value
    spot_prices["timestamp"] = trade_data["timestamp"]
    spot_prices = spot_prices.set_index("timestamp")

    ohlcv = spot_prices.groupby([pd.Grouper(freq=freq)]).agg(
        {"spot_price": ["first", "last", "max", "min"], "value": "sum"}
    )

    ohlcv.columns = ["Open", "Close", "High", "Low", "Volume"]
    ohlcv.index.name = "Date"

    return ohlcv
