# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
"""simulation for the Hyperdrive market"""
from __future__ import annotations

import mplfinance as mpf
import pandas as pd


# %%
def calc_ohlcv(pool_df, freq="D"):
    """
    freq var: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
    """
    # value is change in bondReserves
    value = pool_df["bondReserves"] - pool_df["bondReserves"].shift(1)
    value.iloc[0] = 0

    pool_df["timestamp"] = pd.to_datetime(pool_df["timestamp"], unit="s")
    pool_df["value"] = value / 1e18
    pool_df["value"] = pool_df["value"].astype("float64")
    pool_df = pool_df.set_index("timestamp")

    ohlcv = pool_df.groupby([pd.Grouper(freq=freq)]).agg(
        {"spot_price": ["first", "last", "max", "min"], "value": "sum"}
    )

    ohlcv.columns = ["Open", "Close", "High", "Low", "Volume"]
    ohlcv.index.name = "Date"

    return ohlcv


def plot_ohlcv(ohlcv, ohlcv_ax, vol_ax):
    """Plots the ohlcv plot"""
    mpf.plot(ohlcv, type="candle", volume=vol_ax, ax=ohlcv_ax)

    ohlcv_ax.set_xlabel("block timestamp")
    ohlcv_ax.set_title("OHLCV")
    ohlcv_ax.yaxis.set_label_position("right")
    ohlcv_ax.yaxis.tick_right()

    vol_ax.set_xlabel("block timestamp")
    vol_ax.set_ylabel("Volume")
    vol_ax.set_title("Volume")
    vol_ax.yaxis.set_label_position("right")
    vol_ax.yaxis.tick_right()

    # format x-axis as time
