"""Streamlit wallet stats dashboard"""
# pylint: disable=invalid-name
# Streamlit gets the name of the sidebar tab from the name of the file
# hence, this file is capitalized

import gc

import matplotlib.pyplot as plt
import mplfinance as mpf
import streamlit as st
from chainsync.dashboard import build_ticker, build_user_mapping, map_addresses
from chainsync.db.base import initialize_session
from chainsync.db.hyperdrive import (
    get_all_traders,
    get_ticker,
    get_total_wallet_pnl_over_time,
    get_wallet_pnl,
    get_wallet_positions_over_time,
)

plt.close("all")
gc.collect()

st.set_page_config(page_title="Trading Competition Dashboard", layout="wide")
st.set_option("deprecation.showPyplotGlobalUse", False)

# TODO clean up this script into various functions

MAX_LIVE_BLOCKS = 5000

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
# Get corresponding usernames
user_map = build_user_mapping(session, trader_addrs)

# TODO does this take series? Or do I need to cast this as a list
# TODO there is a case that format_name is not unique, where we should use the wallet addresses
selected = st.multiselect("Wallet Addresses", user_map["format_name"])
# Map selected_addrs back to actual addresses
selected_addresses = map_addresses(selected, user_map, "format_name")["address"].to_list()

# Get ticker for selected addresses
ticker = get_ticker(session, start_block=-MAX_LIVE_BLOCKS, coerce_float=False, wallet_address=selected_addresses)
display_ticker = build_ticker(ticker, user_map)

# Get latest wallet pnls for selected addresses
latest_wallet_pnl = get_wallet_pnl(session, start_block=-1, coerce_float=False, wallet_address=selected_addresses)
# Do lookup of addresses and (1) add username column, and (2) replace walletAddress with abbr address
mapped = map_addresses(latest_wallet_pnl["walletAddress"], user_map)
latest_wallet_pnl["username"] = mapped["username"]
latest_wallet_pnl["walletAddress"] = mapped["abbr_address"]
# Reorder and get subset of dataframe
latest_wallet_pnl = latest_wallet_pnl[
    ["timestamp", "blockNumber", "username", "walletAddress", "tokenType", "value", "pnl"]
]

# Show all dataframes
st.write("Total PnL")
latest_pnl = (
    latest_wallet_pnl.groupby("walletAddress")
    .agg({"username": "first", "pnl": "sum"})
    .sort_values("pnl", ascending=False)
)
st.dataframe(latest_pnl.astype(str), use_container_width=True)

st.write("Current Open Positions")
st.dataframe(latest_wallet_pnl.astype(str), height=300, use_container_width=True, hide_index=True)

st.write("Transactions")
st.dataframe(display_ticker, height=500, use_container_width=True)

# Get PNL over time
pnl_over_time = get_total_wallet_pnl_over_time(
    session, start_block=-MAX_LIVE_BLOCKS, coerce_float=False, wallet_address=selected_addresses
)
# Add username
pnl_over_time["username"] = map_addresses(pnl_over_time["walletAddress"], user_map)["username"]
wallet_positions = get_wallet_positions_over_time(
    session, start_block=-MAX_LIVE_BLOCKS, coerce_float=False, wallet_address=selected_addresses
)
wallet_positions["username"] = map_addresses(wallet_positions["walletAddress"], user_map)["username"]

# Plot pnl over time
main_fig = mpf.figure(style="mike", figsize=(10, 10))
# matplotlib doesn't play nice with types
(ax_pnl, ax_base, ax_long, ax_short, ax_lp, ax_withdraw) = main_fig.subplots(6, 1, sharex=True)  # type: ignore

for addr in pnl_over_time["walletAddress"].unique():
    format_name = map_addresses(addr, user_map)["format_name"]
    wallet_pnl_over_time = pnl_over_time[pnl_over_time["walletAddress"] == addr]
    ax_pnl.plot(wallet_pnl_over_time["timestamp"], wallet_pnl_over_time["pnl"], label=format_name)
ax_pnl.yaxis.set_label_position("right")
ax_pnl.yaxis.tick_right()
ax_pnl.set_xlabel("block timestamp")
ax_pnl.set_ylabel("PnL")
ax_pnl.set_title("PnL Over Time")

# Plot open positions over time
labels = []
for addr in wallet_positions["walletAddress"].unique():
    format_name = map_addresses(addr, user_map)["format_name"]
    labels.append(format_name)
    wallet_positions_over_time = wallet_positions[wallet_positions["walletAddress"] == addr]
    base_positions = wallet_positions_over_time[wallet_positions_over_time["baseTokenType"] == "BASE"][
        ["timestamp", "value"]
    ]
    long_positions = wallet_positions_over_time[wallet_positions_over_time["baseTokenType"] == "LONG"][
        ["timestamp", "value"]
    ]
    short_positions = wallet_positions_over_time[wallet_positions_over_time["baseTokenType"] == "SHORT"][
        ["timestamp", "value"]
    ]
    lp_positions = wallet_positions_over_time[wallet_positions_over_time["baseTokenType"] == "LP"][
        ["timestamp", "value"]
    ]
    withdraw_positions = wallet_positions_over_time[wallet_positions_over_time["baseTokenType"] == "WITHDRAWAL_SHARE"][
        ["timestamp", "value"]
    ]
    ax_base.plot(base_positions["timestamp"], base_positions["value"], label=format_name)
    ax_long.plot(long_positions["timestamp"], long_positions["value"], label=format_name)
    ax_short.plot(short_positions["timestamp"], short_positions["value"], label=format_name)
    ax_lp.plot(lp_positions["timestamp"], lp_positions["value"], label=format_name)
    ax_withdraw.plot(withdraw_positions["timestamp"], withdraw_positions["value"], label=format_name)

all_ax = [ax_base, ax_long, ax_short, ax_lp, ax_withdraw]
y_labels = ["Base", "Bonds", "Bonds", "LP", "Withdraw"]
titles = ["Base Positions", "Long Positions", "Short Positions", "LP Positions", "Withdraw Positions"]
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

st.write("PnL Over Time")
# matplotlib doesn't play nice with types
st.pyplot(fig=main_fig, clear_figure=True, use_container_width=True)  # type: ignore
