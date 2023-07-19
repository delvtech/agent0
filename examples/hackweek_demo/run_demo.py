""" Script to run the streamlab demo """

from __future__ import annotations

import time

import mplfinance as mpf
import pandas as pd
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


# Helper functions
# TODO should likely move these functions to another file
def get_ticker(data: pd.DataFrame) -> pd.DataFrame:
    """Given transaction data, return a ticker dataframe showing recent trades

    Arguments
    ---------
    data: pd.DataFrame
        The dataframe resulting from postgres.get_transactions

    Returns
    -------
    pd.DataFrame
        The filtered transaction data based on what we want to view in the ticker
    """
    # Return reverse of methods to put most recent transactions at the top
    return data[["input_method"]].iloc[::-1]


def get_user_lookup() -> pd.DataFrame:
    """Helper function to generate username -> agents mapping

    Returns
    -------
    pd.DataFrame
        A dataframe with an "username" and "address" columns that provide a lookup
        between a registered username and a wallet address. The username can also be
        the wallet address itself if a wallet is found without a registered username.
    """
    # Get data
    agents = postgres.get_agents(session, start_block=start_block)
    user_map = postgres.get_user_map(session)

    # Generate a lookup of users -> address, taking into account that some addresses don't have users
    # Reindex looks up agent addresses against user_map, adding nans if it doesn't exist
    options_map = user_map.set_index("address").reindex(agents)

    # Set username as address if agent doesn't exist
    na_idx = options_map["username"].isna()
    # If there are any nan usernames, set address itself as username
    if na_idx.any():
        options_map[na_idx] = options_map.index[na_idx]
    return options_map.reset_index()


def username_to_address(lookup: pd.DataFrame, selected_list: list[str]) -> list[str]:
    """Helper function to lookup selected users/addrs to all addresses

    Arguments
    ---------
    lookup: pd.DataFrame
        The lookup dataframe from `get_user_lookup` call
    selected_list: list[str]
        A list of selected values from the multiselect input widget
        These values can either be usernames or addresses

    Returns
    -------
    list[str]
        A list of addresses based on selected_list
    """
    return lookup.set_index("username").loc[selected_list]["address"].tolist()


# Connect to postgres
load_dotenv()
session = postgres.initialize_session()

# Determine if we want to view only a specific window of data
if view_window is not None:
    start_block = -view_window
else:
    start_block = None

# pool config data is static, so just read once
config_data = postgres.get_pool_config(session)

# Set up agent selection state list outside of live updates
st.session_state.options = []


# Initialize select options for filtering
user_lookup = get_user_lookup()
if "agent_list" not in st.session_state:
    st.session_state["agent_list"] = user_lookup["username"].unique().tolist()
if "selected_agents" not in st.session_state:
    st.session_state["selected_agents"] = []
if "all_checkbox" not in st.session_state:
    st.session_state.all_checkbox = False

st.session_state.selected_agents = st.multiselect("PNL Agents", st.session_state.agent_list, key="agent_select")
# All checkbox
st.session_state.all_checkbox = st.checkbox("View all", value=True)

# TODO Seperate out these figures
# TODO abstract out creating a streamlit container + adding a figure

# Initialize streamlit containers for display
main_placeholder = st.empty()
sidebar_placeholder = st.sidebar.empty()
lp_plot_placeholder = st.empty()

fig = mpf.figure(style="mike", figsize=(15, 15))  # type: ignore
ax_ohlcv = fig.add_subplot(2, 2, 1)
ax_fixed_rate = fig.add_subplot(2, 2, 2)
ax_vol = fig.add_subplot(2, 2, 3)
ax_pnl = fig.add_subplot(2, 2, 4)

lp_fig = mpf.figure(style="mike", figsize=(10, 10))  # type: ignore
ax_lp_token = lp_fig.add_subplot(1, 1, 1)
lp_fig.set_tight_layout(True)  # type: ignore


# Main data loop
while True:
    pool_config_data = postgres.get_pool_config(session)
    txn_data = postgres.get_transactions(session, start_block=start_block)
    pool_info_data = postgres.get_pool_info(session, start_block=start_block)
    checkpoint_info = postgres.get_checkpoint_info(session, start_block=start_block)
    if st.session_state.all_checkbox:
        agent_positions = postgres.get_agent_positions(session)
    else:
        selected_addrs = username_to_address(user_lookup, st.session_state.selected_agents)
        agent_positions = postgres.get_agent_positions(session, selected_addrs)

    # No data, wait
    if len(pool_info_data) == 0 or len(txn_data) == 0:
        time.sleep(0.1)
        continue

    # truncate the length of pool_info_data and checkpoint_info to the shorter of their two indexes.
    latest_block = min(max(pool_info_data.index), max(checkpoint_info.index))
    pool_info_data = pool_info_data.loc[:latest_block, :]
    checkpoint_info = checkpoint_info.loc[:latest_block, :]
    combined_data = get_combined_data(txn_data, pool_info_data)

    # Calculate data
    ohlcv = calc_ohlcv(combined_data, freq="5T")
    (fixed_rate_x, fixed_rate_y) = calc_fixed_rate(combined_data)
    all_agent_info = calculate_pnl(pool_config_data, pool_info_data, checkpoint_info, agent_positions)
    ticker = get_ticker(txn_data)

    # Place data and plots
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
        plot_pnl(all_agent_info, ax_pnl)

        # Fix axes labels
        fig.autofmt_xdate()  # type: ignore
        st.pyplot(fig=fig)  # type: ignore

    with lp_plot_placeholder.container():
        ax_lp_token.clear()
        # TODO extract this out
        num_lp_tokens = [ap.positions.loc[:, "LP"] for ap in agent_positions.values()]
        if len(num_lp_tokens) > 0:
            lp_data = pd.concat(num_lp_tokens, axis=1)
            lp_data.columns = [addr for addr in agent_positions.keys()]
            lp_data["lpTotalSupply"] = pool_info_data["lpTotalSupply"]
        else:
            lp_data = pool_info_data["lpTotalSupply"].to_frame()

        ax_lp_token.plot(lp_data.sort_index(), label=lp_data.columns)
        ax_lp_token.legend()
        ax_lp_token.set_xlabel("block number")
        ax_lp_token.set_ylabel("Number LP tokens")
        ax_lp_token.set_title("LP Tokens over blocks")
        st.pyplot(fig=lp_fig)  # type: ignore

    time.sleep(0.1)
