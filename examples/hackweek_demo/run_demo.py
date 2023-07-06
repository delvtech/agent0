""" Script to run the streamlab demo """

from __future__ import annotations

import time

import mplfinance as mpf
import streamlit as st
from dotenv import load_dotenv
from extract_data_logs import get_combined_data
from plot_fixed_rate import calc_fixed_rate, plot_fixed_rate
from plot_ohlcv import calc_ohlcv, plot_ohlcv
from plot_pnl import calculate_pnl, plot_pnl

from elfpy.data import postgres

# pylint: disable=invalid-name

# The number of blocks to view at a time, e.g., only the last 500 blocks
# None to view all
view_window = None

# set up streamlit
# creating a single-element container
placeholder = st.empty()

# %%
# near real-time / live feed simulation

## Get transactions from data


def get_ticker(data):
    """Given transaction data, return a subset of the dataframe"""
    # Return reverse of methods to put most recent transactions at the top
    out = data[["blockNumber", "input_method"]].set_index("blockNumber").iloc[::-1]
    return out


fig = mpf.figure(style="mike", figsize=(15, 15))  # type: ignore
ax_ohlcv = fig.add_subplot(2, 2, 1)
ax_fixed_rate = fig.add_subplot(2, 2, 2)
ax_vol = fig.add_subplot(2, 2, 3)
ax_pnl = fig.add_subplot(2, 2, 4)
fig.set_tight_layout(True)  # type: ignore


load_dotenv()
session = postgres.initialize_session()

if view_window is not None:
    start_block = -view_window
else:
    start_block = None

# pool config data is static, so just read once
config_data = postgres.get_pool_config(session)

while True:
    txn_data = postgres.get_transactions(session, start_block=start_block)
    pool_info_data = postgres.get_pool_info(session, start_block=start_block)

    combined_data = get_combined_data(txn_data, pool_info_data)

    ohlcv = calc_ohlcv(combined_data, freq="5T")

    ticker = get_ticker(txn_data)

    (fixed_rate_x, fixed_rate_y) = calc_fixed_rate(combined_data)

    pnl_x, pnl_y = calculate_pnl(combined_data)

    # Plot reserve levels (share and bond reserves, in poolinfo)

    # Fix axes labels

    # Add ticker

    with placeholder.container():
        ticker_col, plots_col = st.columns([0.2, 1], gap="small")
        with ticker_col:
            st.dataframe(ticker.iloc[:100], height=900, width=170)

        with plots_col:
            # Clears all axes
            ax_ohlcv.clear()
            ax_fixed_rate.clear()
            ax_vol.clear()
            ax_pnl.clear()

            # TODO add in volume
            plot_ohlcv(ohlcv, ax_ohlcv, ax_vol)
            plot_fixed_rate(fixed_rate_x, fixed_rate_y, ax_fixed_rate)
            plot_pnl(pnl_x, pnl_y, ax_pnl)

            fig.autofmt_xdate()  # type: ignore
            st.pyplot(fig=fig)  # type: ignore

    time.sleep(0.1)
