"""Builds the ohlcv dataframe for the dashboard."""

import pandas as pd


def build_ohlcv(pool_analysis, freq="D") -> pd.DataFrame:
    """Builds the ohlcv dataframe ready to be plot

    Arguments
    ---------
    pool_analysis: pd.DataFrame
        The pool analysis object from `get_pool_anlysis`
    freq: str
        The grouping frequency for the ohlcv plot.
        See https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
        for accepted values

    Returns
    -------
    pd.DataFrame
        The ready to plot dataframe for ohlcv
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
