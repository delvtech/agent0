"""Streamlit wallet stats dashboard"""

# pylint: disable=invalid-name
# Streamlit gets the name of the sidebar tab from the name of the file
# hence, this file is capitalized

import gc

import matplotlib.pyplot as plt
import mplfinance as mpf
import streamlit as st

from agent0.chainsync.dashboard import build_user_mapping, build_wallet_dashboard, map_addresses, reduce_plot_data
from agent0.chainsync.db.base import get_addr_to_username, initialize_session
from agent0.chainsync.db.hyperdrive import get_all_traders

plt.close("all")
gc.collect()

st.set_page_config(page_title="Trading Competition Dashboard", layout="wide")
st.set_option("deprecation.showPyplotGlobalUse", False)

# Load and connect to postgres
session = initialize_session()

# Refresh button
# Streamlit automatically refreshes when an input widget is changed
# so just having this button clicked automatically refreshes
# Magic.
st.button("Refresh")


# Multiselect box of all available agents
# Get all addresses that have made a trade
trader_addrs = get_all_traders(session)
addr_to_username = get_addr_to_username(session)

# Get corresponding usernames
user_map = build_user_mapping(trader_addrs, addr_to_username)

# TODO does this take series? Or do I need to cast this as a list
# TODO there is a case that format_name is not unique, where we should use the wallet addresses
selected = st.multiselect("Wallet Addresses", user_map["format_name"])

if len(selected) > 0:
    # Map selected_addrs back to actual addresses
    selected_addresses = map_addresses(selected, user_map, "format_name")["address"].to_list()

    data_dfs = build_wallet_dashboard(selected_addresses, user_map=user_map, session=session)

    # Show all dataframes
    st.write("Total PnL")
    st.dataframe(data_dfs["total_pnl"], use_container_width=True)

    st.write("Per Pool PnL")
    st.dataframe(data_dfs["pool_pnl"], use_container_width=True)

    st.write("Open Positions")
    st.dataframe(data_dfs["open_positions"], height=300, use_container_width=True, hide_index=True)

    st.write("Closed Positions")
    st.dataframe(data_dfs["closed_positions"], height=300, use_container_width=True, hide_index=True)

    st.write("Transactions")
    st.dataframe(data_dfs["display_ticker"], height=500, use_container_width=True)

    # Plot pnl over time
    main_fig = mpf.figure(style="mike", figsize=(10, 10))
    # matplotlib doesn't play nice with types
    (ax_pnl, ax_base, ax_long, ax_short, ax_lp, ax_withdraw) = main_fig.subplots(6, 1, sharex=True)  # type: ignore

    pnl_over_time = data_dfs["pnl_over_time"]
    for addr in data_dfs["pnl_over_time"]["wallet_address"].unique():
        format_name = map_addresses(addr, user_map)["format_name"]
        wallet_pnl_over_time = pnl_over_time[pnl_over_time["wallet_address"] == addr]
        wallet_pnl_over_time = reduce_plot_data(wallet_pnl_over_time, "timestamp", "pnl")
        ax_pnl.plot(wallet_pnl_over_time["timestamp"], wallet_pnl_over_time["pnl"], label=format_name)

    ax_pnl.yaxis.set_label_position("right")
    ax_pnl.yaxis.tick_right()
    ax_pnl.set_xlabel("block timestamp")
    ax_pnl.set_ylabel("PnL")
    ax_pnl.set_title("PnL Over Time")

    # Plot open positions over time
    labels = []
    positions_over_time = data_dfs["positions_over_time"]
    realized_value_over_time = data_dfs["realized_value_over_time"]
    for addr in positions_over_time["wallet_address"].unique():
        format_name = map_addresses(addr, user_map)["format_name"]
        labels.append(format_name)

        wallet_realized_value_over_time = realized_value_over_time[realized_value_over_time["wallet_address"] == addr]
        wallet_realized_value_over_time = reduce_plot_data(
            wallet_realized_value_over_time,
            x_column_name="timestamp",
            y_column_name="realized_value",
        )

        wallet_positions_over_time = positions_over_time[positions_over_time["wallet_address"] == addr]
        long_positions = reduce_plot_data(
            wallet_positions_over_time[wallet_positions_over_time["token_type"] == "LONG"],
            x_column_name="timestamp",
            y_column_name="token_balance",
        )
        short_positions = reduce_plot_data(
            wallet_positions_over_time[wallet_positions_over_time["token_type"] == "SHORT"],
            x_column_name="timestamp",
            y_column_name="token_balance",
        )
        lp_positions = reduce_plot_data(
            wallet_positions_over_time[wallet_positions_over_time["token_type"] == "LP"],
            x_column_name="timestamp",
            y_column_name="token_balance",
        )
        withdraw_positions = reduce_plot_data(
            wallet_positions_over_time[wallet_positions_over_time["token_type"] == "WITHDRAWAL_SHARE"],
            x_column_name="timestamp",
            y_column_name="token_balance",
        )
        ax_base.plot(
            wallet_realized_value_over_time["timestamp"],
            wallet_realized_value_over_time["realized_value"],
            label=format_name,
        )
        ax_long.plot(long_positions["timestamp"], long_positions["token_balance"], label=format_name)
        ax_short.plot(short_positions["timestamp"], short_positions["token_balance"], label=format_name)
        ax_lp.plot(lp_positions["timestamp"], lp_positions["token_balance"], label=format_name)
        ax_withdraw.plot(withdraw_positions["timestamp"], withdraw_positions["token_balance"], label=format_name)

    all_ax = [ax_base, ax_long, ax_short, ax_lp, ax_withdraw]
    y_labels = ["base", "longs", "shorts", "LP", "Withdraw"]
    titles = ["Realized Base", "Long Positions", "Short Positions", "LP Positions", "Withdraw Positions"]
    for ax, y_label, title in zip(all_ax, y_labels, titles):
        ax.yaxis.set_label_position("right")
        ax.yaxis.tick_right()
        ax.set_xlabel("block timestamp")
        ax.set_ylabel(y_label)
        ax.set_title(title)

    main_fig.legend(labels=labels, loc="center left", bbox_to_anchor=(1, 0.5))
    # Fix axes labels
    main_fig.autofmt_xdate()
    # matplotlib doesn't play nice with types
    main_fig.tight_layout()  # type: ignore

    st.write("Positions Over Time")
    # matplotlib doesn't play nice with types
    st.pyplot(fig=main_fig, clear_figure=True, use_container_width=True)  # type: ignore
