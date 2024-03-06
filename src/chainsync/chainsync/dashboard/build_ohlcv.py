"""Builds the ohlcv dataframe for the dashboard."""

from __future__ import annotations

import pandas as pd


def build_ohlcv(pool_analysis: pd.DataFrame, freq: str | None = None) -> pd.DataFrame:
    """Builds the ohlcv dataframe ready to be plot

    Arguments
    ---------
    pool_analysis: pd.DataFrame
        The pool analysis object from `get_pool_anlysis`
    freq: str | None
        The grouping frequency for the ohlcv plot.
        See https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
        for accepted values
        If none, defaults to 5min

    Returns
    -------
    pd.DataFrame
        The ready to plot dataframe for ohlcv
    """
    if freq is None:
        freq = "5min"

    spot_prices = pool_analysis[["timestamp", "spot_price"]].copy()
    spot_prices = spot_prices.set_index("timestamp")
    if len(spot_prices) == 0:
        return pd.DataFrame()

    # TODO this is filling groups without data with nans, is this desired?
    ohlcv = spot_prices.groupby([pd.Grouper(freq=freq)]).agg({"spot_price": ["first", "last", "max", "min"]})

    ohlcv.columns = ["Open", "Close", "High", "Low"]
    ohlcv.index.name = "Date"
    # ohlcv must be floats
    ohlcv = ohlcv.astype(float)

    return ohlcv
