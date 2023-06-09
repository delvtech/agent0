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
from extract_data_logs import read_json_to_pd, explode_transaction_data, calculate_spot_price

import matplotlib.pyplot as plt
import mplfinance as mpf
import streamlit as st
import pandas as pd
import time


# %%
# Get data here
st.set_page_config(
    page_title="Bots dashboard",
    layout="wide",
    )
st.set_option('deprecation.showPyplotGlobalUse', False)

def calc_ohlcv(pool_info_data, freq='D'):
    """
    freq var: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
    """
    spot_prices = calculate_spot_price(pool_info_data).to_frame().astype(float)
    spot_prices.columns = ['spot_price']
    timestamp = pool_info_data['timestamp']
    spot_prices['timestamp'] = pd.to_datetime(timestamp, unit='s')
    spot_prices = spot_prices.set_index('timestamp')

    ohlcv = spot_prices.groupby([
        pd.Grouper(freq=freq)
    ]).agg({'spot_price':['first', 'last', 'max', 'min']})

    ohlcv.columns = ['Open', 'Close', 'High', 'Low']
    ohlcv.index.name = 'Date'

    return ohlcv

# creating a single-element container
placeholder = st.empty()

# %%
# near real-time / live feed simulation

while True:
    # Hard coding location for now
    # trans_data = "hyperTransRecs_updated.json"

    ## Get transactions from data
    trans_data = "../../.logging/transactions.json"
    config_data = "../../.logging/hyperdrive_config.json"
    pool_info_data = "../../.logging/hyperdrive_pool_info.json"

    trans_data = explode_transaction_data(read_json_to_pd(trans_data))
    config_data = read_json_to_pd(config_data)
    pool_info_data = read_json_to_pd(pool_info_data).T

    ohlcv = calc_ohlcv(pool_info_data, freq='5T')

    with placeholder.container():
        # create three columns
        fig_col = st.columns(1)[0]
        plt.close('all')
        fig = mpf.plot(ohlcv, style='mike', type='candle', returnfig=True)
        with fig_col:
            st.markdown("## OHLCV plot")
            st.write(fig[0])

    time.sleep(.1)

