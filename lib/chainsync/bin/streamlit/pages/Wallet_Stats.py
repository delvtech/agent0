"""Stereamlit wallet stats dashboard"""

import mplfinance as mpf
import streamlit as st
from chainsync.dashboard import build_ticker, get_user_lookup
from chainsync.db.base import get_user_map, initialize_session
from chainsync.db.hyperdrive import get_all_traders, get_ticker, get_wallet_pnl

st.set_page_config(page_title="Trading Competition Dashboard", layout="wide")
st.set_option("deprecation.showPyplotGlobalUse", False)

# TODO clean up this script into various functions

max_live_blocks = 14400

# Load and connect to postgres
session = initialize_session()

# Get username lookup
agents = get_all_traders(session)
user_map = get_user_map(session)
user_lookup = get_user_lookup(agents, user_map, keep_nans=True).copy()

# Format user lookup as a combination of address + username (if username exists)
na_username = user_lookup["username"].isna()
user_lookup.loc[na_username, "username"] = ""
user_lookup["format_name"] = (
    user_lookup["username"] + " - " + user_lookup["address"].str[:6] + "..." + user_lookup["address"].str[-4:]
)

# Multiselect box of all available agents
selected = st.multiselect("Wallet Addresses", user_lookup["format_name"])

# Map selected_addrs back to actual addresses
selected_addresses = user_lookup.set_index("format_name").loc[selected]["address"].values.tolist()

# Get wallet pnls for selected addresses
wallet_pnl = get_wallet_pnl(
    session, start_block=-max_live_blocks, coerce_float=False, wallet_address=selected_addresses
)

# Get ticker for selected addresses
ticker = get_ticker(session, coerce_float=False, wallet_address=selected_addresses)
display_ticker = build_ticker(ticker, user_lookup)

# Get latest wallet pnl and show open positions
wallet_pnl = wallet_pnl.drop(["id", "baseTokenType", "maturityTime"], axis=1).copy()
latest_wallet_pnl = wallet_pnl[wallet_pnl["blockNumber"] == wallet_pnl["blockNumber"].max()].copy()
# Get usernames
latest_wallet_pnl["username"] = (
    user_lookup.set_index("address").loc[latest_wallet_pnl["walletAddress"]]["username"].values
)
# Shorten wallet address
latest_wallet_pnl["walletAddress"] = (
    latest_wallet_pnl["walletAddress"].str[:6] + "..." + latest_wallet_pnl["walletAddress"].str[-4:]
)
# Reorder dataframe
latest_wallet_pnl = latest_wallet_pnl[
    ["timestamp", "blockNumber", "username", "walletAddress", "tokenType", "value", "pnl"]
]

# Show all dataframes
st.write("Total PnL")
latest_pnl = latest_wallet_pnl.groupby("walletAddress").agg({"username": "first", "pnl": "sum"})
st.dataframe(latest_pnl.astype(str), use_container_width=True)

st.write("Current Open Positions")
st.dataframe(latest_wallet_pnl.astype(str), height=300, use_container_width=True, hide_index=True)

st.write("Transactions")
st.dataframe(display_ticker, height=500, use_container_width=True)

# Calculate pnl over time
pnl_over_time = wallet_pnl.groupby(["walletAddress", "blockNumber"]).agg({"pnl": "sum", "timestamp": "first"})
pnl_over_time = pnl_over_time.reset_index()

# Plot pnl over time
main_fig = mpf.figure(style="mike", figsize=(15, 5))
ax_pnl = main_fig.add_subplot(1, 1, 1)
for addr in pnl_over_time["walletAddress"].unique():
    format_name = user_lookup.set_index("address").loc[addr]["format_name"]
    wallet_pnl_over_time = pnl_over_time[pnl_over_time["walletAddress"] == addr]
    ax_pnl.plot(wallet_pnl_over_time["timestamp"], wallet_pnl_over_time["pnl"], label=format_name)
ax_pnl.yaxis.set_label_position("right")
ax_pnl.yaxis.tick_right()
ax_pnl.set_xlabel("block timestamp")
ax_pnl.set_ylabel("PnL")
ax_pnl.set_title("PnL Over Time")
ax_pnl.legend()

st.write("PnL Over Time")
st.pyplot(fig=main_fig)
