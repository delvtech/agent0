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
from extract_data_logs import calculate_spot_price
from matplotlib import dates as mdates

import mplfinance as mpf
import streamlit as st
import pandas as pd


# %%
# Get data here
st.set_page_config(
    page_title="Bots dashboard",
    layout="wide",
)
st.set_option("deprecation.showPyplotGlobalUse", False)


def calc_ohlcv(trade_data, freq="D"):
    """
    freq var: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
    """
    spot_prices = calculate_spot_price(
            share_reserves = trade_data["share_reserves"],
            bond_reserves = trade_data["bond_reserves"],
            lp_total_supply = trade_data["lp_total_supply"],
            ).to_frame().astype(float)

    spot_prices.columns = ["spot_price"]
    timestamp = trade_data["block_timestamp"]
    value = trade_data["value"]

    spot_prices["timestamp"] = pd.to_datetime(timestamp, unit="s")
    spot_prices["value"] = value
    spot_prices = spot_prices.set_index("timestamp")

    ohlcv = spot_prices.groupby([pd.Grouper(freq=freq)]).agg({"spot_price": ["first", "last", "max", "min"], "value": "sum"})

    ohlcv.columns = ["Open", "Close", "High", "Low", "Volume"]
    ohlcv.index.name = "Date"

    return ohlcv

def plot_ohlcv(ohlcv, ax, vol_ax):
    """Plots the ohlcv plot"""
    mpf.plot(ohlcv, type="candle", volume=vol_ax, ax=ax)


    ax.set_xlabel("block timestamp")
    ax.set_title("OHLCV")
    ax.yaxis.set_label_position('right')
    ax.yaxis.tick_right()

    vol_ax.set_xlabel("block timestamp")
    vol_ax.set_ylabel("Volume")
    vol_ax.set_title("Volume")
    vol_ax.yaxis.set_label_position('right')
    vol_ax.yaxis.tick_right()



    # format x-axis as time





