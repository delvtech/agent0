"""Run the dashboard."""

# pylint: disable=invalid-name
# Streamlit gets the name of the sidebar tab from the name of the file
# hence, this file is capitalized

from __future__ import annotations

import gc
import time

import matplotlib.pyplot as plt
import mplfinance as mpf
import streamlit as st

from agent0.chainsync.dashboard import (
    abbreviate_address,
    build_pool_dashboard,
    plot_ohlcv,
    plot_outstanding_positions,
    plot_rates,
)
from agent0.chainsync.db.base import initialize_session
from agent0.chainsync.db.hyperdrive import get_hyperdrive_addr_to_name

# pylint: disable=invalid-name

plt.close("all")
gc.collect()

st.set_page_config(page_title="Trading Competition Dashboard", layout="wide")

# Load and connect to postgres
session = initialize_session()


# This assumes all pools that have events logged are registered in this table.
hyperdrive_addr_mapping = get_hyperdrive_addr_to_name(session)
# Append the short addr to the pool name
hyperdrive_addr_mapping["print_name"] = (
    hyperdrive_addr_mapping["name"].replace("_", " ")
    + " ("
    + abbreviate_address(hyperdrive_addr_mapping["hyperdrive_address"])
    + ")"
)
selected_hyperdrive_address = st.selectbox("Hyperdrive Pool", hyperdrive_addr_mapping["print_name"])

# Live ticker
ticker_placeholder = st.empty()
# Live leaderboard
leaderboard_placeholder = st.empty()
# OHLCV
main_placeholder = st.empty()

main_fig = mpf.figure(style="mike", figsize=(10, 10))
# matplotlib doesn't play nice with types
(ax_ohlcv, ax_fixed_rate, ax_positions) = main_fig.subplots(3, 1, sharex=True)  # type: ignore

while True:
    if selected_hyperdrive_address is not None:
        hyperdrive_address = hyperdrive_addr_mapping[
            hyperdrive_addr_mapping["print_name"] == selected_hyperdrive_address
        ].iloc[0]["hyperdrive_address"]
        data_dfs = build_pool_dashboard(hyperdrive_address, session)

        with ticker_placeholder.container():
            st.header("Ticker")
            st.dataframe(data_dfs["display_ticker"], height=200, use_container_width=True)

        with leaderboard_placeholder.container():
            st.header("Wallet Leaderboard")
            st.dataframe(data_dfs["leaderboard"], height=500, use_container_width=True)

        with main_placeholder.container():
            # Clears all axes
            ax_ohlcv.clear()
            ax_fixed_rate.clear()
            ax_positions.clear()

            plot_ohlcv(data_dfs["ohlcv"], ax_ohlcv)
            plot_rates(data_dfs["fixed_rate"], data_dfs["variable_rate"], ax_fixed_rate)
            plot_outstanding_positions(data_dfs["outstanding_positions"], ax_positions)

            ax_ohlcv.tick_params(axis="both", which="both")
            ax_fixed_rate.tick_params(axis="both", which="both")
            # Fix axes labels
            main_fig.autofmt_xdate()
            # streamlit doesn't play nice with types
            st.pyplot(fig=main_fig)  # type: ignore
    # Slow down refreshes
    time.sleep(1)
