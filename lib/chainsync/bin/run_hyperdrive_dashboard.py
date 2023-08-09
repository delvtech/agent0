"""Run the streamlab demo."""
from __future__ import annotations

import os
import time

import mplfinance as mpf
import pandas as pd
import streamlit as st
from agent0.hyperdrive.config import get_eth_bots_config
from chainsync.analysis.calc_fixed_rate import calc_fixed_rate
from chainsync.analysis.calc_ohlcv import calc_ohlcv
from chainsync.analysis.calc_pnl import calc_closeout_pnl, calc_total_returns
from chainsync.base import initialize_session
from chainsync.dashboard import (
    build_leaderboard,
    build_ticker,
    get_combined_data,
    get_user_lookup,
    plot_fixed_rate,
    plot_ohlcv,
)
from chainsync.hyperdrive import get_pool_config, get_pool_info, get_transactions, get_wallet_deltas
from dotenv import load_dotenv

# pylint: disable=invalid-name

st.set_page_config(page_title="Trading Competition Dashboard", layout="wide")
st.set_option("deprecation.showPyplotGlobalUse", False)

# Connect to postgres
load_dotenv()
session = initialize_session()

# TODO remove this connection and add in process to periodically calculate closing pnl
# Adding these configs from env variables as a temp workaround
env_config, _ = get_eth_bots_config()
# Look for env variables and overwrite if they exist
artifacts_url = os.getenv("ARTIFACTS_URL")
if artifacts_url is not None:
    env_config["artifacts_url"] = artifacts_url
rpc_url = os.getenv("RPC_URL")
if rpc_url is not None:
    env_config["rpc_url"] = rpc_url


# pool config data is static, so just read once
config_data = get_pool_config(session, coerce_float=False)

# TODO fix input invTimeStretch to be unscaled in ingestion into postgres
config_data["invTimeStretch"] = config_data["invTimeStretch"] / 10**18

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
    # Place data and plots
    user_lookup = get_user_lookup(session)
    txn_data = get_transactions(session, -max_live_blocks)
    pool_info_data = get_pool_info(session, -max_live_blocks, coerce_float=False)
    combined_data = get_combined_data(txn_data, pool_info_data)
    wallet_deltas = get_wallet_deltas(session, coerce_float=False)
    ticker = build_ticker(wallet_deltas, txn_data, pool_info_data, user_lookup)

    (fixed_rate_x, fixed_rate_y) = calc_fixed_rate(combined_data, config_data)
    ohlcv = calc_ohlcv(combined_data, config_data, freq="5T")

    current_returns, current_wallet = calc_total_returns(config_data, pool_info_data, wallet_deltas)
    current_wallet = calc_closeout_pnl(current_wallet, pool_info_data, env_config)  # calc pnl using closeout method
    current_wallet.delta = current_wallet.delta.astype(float)
    current_wallet.pnl = current_wallet.pnl.astype(float)
    current_wallet.closeout_pnl = current_wallet.closeout_pnl.astype(float)
    ## TODO: FIX BOT RESTARTS
    ## Add initial budget column to bots
    ## when bot restarts, use initial budget for bot's wallet address to set "budget" in Agent.Wallet

    comb_rank, ind_rank = build_leaderboard(current_returns, user_lookup)

    with ticker_placeholder.container():
        st.header("Ticker")
        st.dataframe(ticker, height=200, use_container_width=True)
        st.header("PNL")
        st.dataframe(current_wallet, height=500, use_container_width=True)
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
        plot_fixed_rate(fixed_rate_x, fixed_rate_y, ax_fixed_rate)

        ax_ohlcv.tick_params(axis="both", which="both")
        ax_vol.tick_params(axis="both", which="both")
        ax_fixed_rate.tick_params(axis="both", which="both")
        # Fix axes labels
        main_fig.autofmt_xdate()
        st.pyplot(fig=main_fig)  # type: ignore

    time.sleep(1)
