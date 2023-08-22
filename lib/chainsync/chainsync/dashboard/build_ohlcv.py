from decimal import Decimal

import pandas as pd


def build_ohlcv(pool_analysis, freq="D"):
    """
    freq var: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
    """
    spot_prices = pool_analysis[["timestamp", "spot_price"]].copy()
    spot_prices = spot_prices.set_index("timestamp")

    # TODO this is filling groups without data with nans, is this desired?
    ohlcv = spot_prices.groupby([pd.Grouper(freq=freq)]).agg({"spot_price": ["first", "last", "max", "min"]})

    ohlcv.columns = ["Open", "Close", "High", "Low"]
    ohlcv.index.name = "Date"
    # ohlcv must be floats
    ohlcv = ohlcv.astype(float)

    return ohlcv
