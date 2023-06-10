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


def calc_ohlcv(pool_info_data, freq="D"):
    """
    freq var: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
    """
    spot_prices = calculate_spot_price(pool_info_data).to_frame().astype(float)
    spot_prices.columns = ["spot_price"]
    timestamp = pool_info_data["timestamp"]
    spot_prices["timestamp"] = pd.to_datetime(timestamp, unit="s")
    spot_prices = spot_prices.set_index("timestamp")

    ohlcv = spot_prices.groupby([pd.Grouper(freq=freq)]).agg({"spot_price": ["first", "last", "max", "min"]})

    ohlcv.columns = ["Open", "Close", "High", "Low"]
    ohlcv.index.name = "Date"

    return ohlcv


def plot_ohlcv(ohlcv):
    """Plots the ohlcv plot"""
    fig = mpf.plot(ohlcv, style="mike", type="candle", returnfig=True)
    return fig
