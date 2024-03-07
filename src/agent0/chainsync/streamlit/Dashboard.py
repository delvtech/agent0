"""Run the dashboard."""

# pylint: disable=invalid-name
# Streamlit gets the name of the sidebar tab from the name of the file
# hence, this file is capitalized

from __future__ import annotations

import gc
import time

import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import streamlit as st

from agent0.chainsync.dashboard import (
    build_fixed_rate,
    build_leaderboard,
    build_ohlcv,
    build_outstanding_positions,
    build_ticker,
    build_user_mapping,
    build_variable_rate,
    plot_ohlcv,
    plot_outstanding_positions,
    plot_rates,
)
from agent0.chainsync.db.base import get_addr_to_username, get_username_to_user, initialize_session
from agent0.chainsync.db.hyperdrive import get_all_traders, get_pool_analysis, get_pool_info, get_ticker, get_wallet_pnl

# pylint: disable=invalid-name

plt.close("all")
gc.collect()

st.set_page_config(page_title="Trading Competition Dashboard", layout="wide")
st.set_option("deprecation.showPyplotGlobalUse", False)

# Load and connect to postgres
session = initialize_session()

max_live_blocks = 5000
max_ticker_rows = 1000
# Live ticker
ticker_placeholder = st.empty()
# OHLCV
main_placeholder = st.empty()

main_fig = mpf.figure(style="mike", figsize=(10, 10))
# matplotlib doesn't play nice with types
(ax_ohlcv, ax_fixed_rate, ax_positions) = main_fig.subplots(3, 1, sharex=True)  # type: ignore

freq = None
while True:
    # Wallet addr to username mapping
    trader_addrs = get_all_traders(session)
    addr_to_username = get_addr_to_username(session)
    username_to_user = get_username_to_user(session)
    user_map = build_user_mapping(trader_addrs, addr_to_username, username_to_user)

    pool_info = get_pool_info(session, start_block=-max_live_blocks, coerce_float=False)
    # TODO generalize this
    # We check the block timestamp difference since we're running
    # either in real time mode or rapid 312 second per block mode
    # Determine which one, and set freq respectively
    if freq is None:
        if len(pool_info) > 2:
            time_diff = pool_info.iloc[-1]["timestamp"] - pool_info.iloc[-2]["timestamp"]
            if time_diff > pd.Timedelta("1min"):
                freq = "D"
            else:
                freq = "5min"

    pool_analysis = get_pool_analysis(session, start_block=-max_live_blocks, coerce_float=False)
    ticker = get_ticker(session, max_rows=max_ticker_rows, coerce_float=False, sort_desc=True)
    # Adds user lookup to the ticker
    display_ticker = build_ticker(ticker, user_map)

    # get wallet pnl and calculate leaderboard
    # Get the latest updated block
    latest_wallet_pnl = get_wallet_pnl(session, start_block=-1, coerce_float=False)
    comb_rank, ind_rank = build_leaderboard(latest_wallet_pnl, user_map)

    # build ohlcv and volume
    ohlcv = build_ohlcv(pool_analysis, freq=freq)
    # build rates
    fixed_rate = build_fixed_rate(pool_analysis)
    variable_rate = build_variable_rate(pool_info)

    # build outstanding positions plots
    outstanding_positions = build_outstanding_positions(pool_info)

    with ticker_placeholder.container():
        st.header("Ticker")
        st.dataframe(display_ticker, height=200, use_container_width=True)
        st.header("Total Leaderboard")
        st.dataframe(comb_rank, height=500, use_container_width=True)
        st.header("Wallet Leaderboard")
        st.dataframe(ind_rank, height=500, use_container_width=True)

    with main_placeholder.container():
        # Clears all axes
        ax_ohlcv.clear()
        ax_fixed_rate.clear()
        ax_positions.clear()

        plot_ohlcv(ohlcv, ax_ohlcv)
        plot_rates(fixed_rate, variable_rate, ax_fixed_rate)
        plot_outstanding_positions(outstanding_positions, ax_positions)

        ax_ohlcv.tick_params(axis="both", which="both")
        ax_fixed_rate.tick_params(axis="both", which="both")
        # Fix axes labels
        main_fig.autofmt_xdate()
        # streamlit doesn't play nice with types
        st.pyplot(fig=main_fig)  # type: ignore

    time.sleep(1)
