"""Run the dashboard."""
from __future__ import annotations

import time

import mplfinance as mpf
import streamlit as st
from chainsync.dashboard import (
    build_fixed_rate,
    build_leaderboard,
    build_ohlcv,
    build_ticker,
    get_user_lookup,
    plot_fixed_rate,
    plot_ohlcv,
)
from chainsync.db.base import get_user_map, initialize_session
from chainsync.db.hyperdrive import get_all_traders, get_pool_analysis, get_pool_config, get_ticker, get_wallet_pnl
from ethpy import build_eth_config

# pylint: disable=invalid-name

st.set_page_config(page_title="Trading Competition Dashboard", layout="wide")
st.set_option("deprecation.showPyplotGlobalUse", False)

# Load and connect to postgres
session = initialize_session()

# TODO remove this connection and add in process to periodically calculate closing pnl
eth_config = build_eth_config()

# pool config data is static, so just read once
config_data = get_pool_config(session, coerce_float=False)

config_data = config_data.iloc[0]


max_live_blocks = 14400
# Live ticker
ticker_placeholder = st.empty()
# OHLCV
main_placeholder = st.empty()

main_fig = mpf.figure(style="mike", figsize=(15, 15))
ax_ohlcv = main_fig.add_subplot(3, 1, 1)
ax_vol = main_fig.add_subplot(3, 1, 2)
ax_fixed_rate = main_fig.add_subplot(3, 1, 3)

while True:
    # Wallet addr to username mapping
    agents = get_all_traders(session)
    user_map = get_user_map(session)
    user_lookup = get_user_lookup(agents, user_map)

    pool_analysis = get_pool_analysis(session, start_block=-max_live_blocks, coerce_float=False)
    ticker = get_ticker(session, start_block=-max_live_blocks, coerce_float=False)
    # Adds user lookup to the ticker
    display_ticker = build_ticker(ticker, user_lookup)

    # get wallet pnl and calculate leaderboard
    wallet_pnl = get_wallet_pnl(session, start_block=-max_live_blocks, coerce_float=False)
    # Get the latest updated block
    latest_wallet_pnl = wallet_pnl[wallet_pnl["blockNumber"] == wallet_pnl["blockNumber"].max()]
    comb_rank, ind_rank = build_leaderboard(latest_wallet_pnl, user_lookup)

    # build ohlcv and volume
    ohlcv = build_ohlcv(pool_analysis, freq="5T")
    # build fixed rate
    fixed_rate = build_fixed_rate(pool_analysis)

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
        ax_vol.clear()
        ax_fixed_rate.clear()

        plot_ohlcv(ohlcv, ax_ohlcv, ax_vol)
        plot_fixed_rate(fixed_rate, ax_fixed_rate)

        ax_ohlcv.tick_params(axis="both", which="both")
        ax_vol.tick_params(axis="both", which="both")
        ax_fixed_rate.tick_params(axis="both", which="both")
        # Fix axes labels
        main_fig.autofmt_xdate()
        st.pyplot(fig=main_fig)  # type: ignore

    time.sleep(1)
