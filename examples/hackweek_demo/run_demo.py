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


# %%
# near real-time / live feed simulation

## Get transactions from data


# TODO should these all be seperate figures instead of one figure?

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

# Set up agent selection state list outside of live updates
st.session_state.options = []


def get_ticker(data):
    """Given transaction data, return a subset of the dataframe"""
    # Return reverse of methods to put most recent transactions at the top
    out = data[["input_method"]].iloc[::-1]
    return out


agent_list = postgres.get_agents(session, start_block=start_block)

filter_agents = st.multiselect("PNL Agents", agent_list, key="agent_select")


# creating a single-element container
main_placeholder = st.empty()
# creating a single-element sidebar
sidebar_placeholder = st.sidebar.empty()


while True:
    txn_data = postgres.get_transactions(session, start_block=start_block)
    pool_info_data = postgres.get_pool_info(session, start_block=start_block)

    combined_data = get_combined_data(txn_data, pool_info_data)

    if len(combined_data) == 0:
        time.sleep(0.1)
        continue

    ohlcv = calc_ohlcv(combined_data, freq="5T")

    ticker = get_ticker(txn_data)

    (fixed_rate_x, fixed_rate_y) = calc_fixed_rate(combined_data)

    pnl_x, pnl_y = calculate_pnl(combined_data, filter_agents)

    # Plot reserve levels (share and bond reserves, in poolinfo)

    # Fix axes labels

    # Add ticker

    # Selection options for filtering agent, defined outside of update loop
    # Session state gets updated inside loop
    # with plots_col:
    with sidebar_placeholder.container():
        st.dataframe(ticker.iloc[:100], height=900, use_container_width=True)

    with main_placeholder.container():
        # Clears all axes
        ax_vol.clear()
        ax_pnl.clear()
        ax_ohlcv.clear()
        ax_fixed_rate.clear()

        plot_ohlcv(ohlcv, ax_ohlcv, ax_vol)
        plot_fixed_rate(fixed_rate_x, fixed_rate_y, ax_fixed_rate)
        plot_pnl(pnl_x, pnl_y, ax_pnl)

        fig.autofmt_xdate()  # type: ignore
        st.pyplot(fig=fig)  # type: ignore

    time.sleep(0.1)
