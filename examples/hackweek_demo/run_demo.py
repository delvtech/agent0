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
from plot_pnl import calculate_current_pnl

from elfpy.data import postgres

# pylint: disable=invalid-name
# Pandas doesn't play nice with types

# The number of blocks to view at a time, e.g., only the last 500 blocks
# None to view all
view_window = None

st.set_page_config(page_title="Trading Competition Dashboard", layout="centered")
st.set_option("deprecation.showPyplotGlobalUse", False)


# Helper functions
# TODO should likely move these functions to another file
def get_ticker(data: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
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

    usernames = username_to_address(lookup, data["operator"])
    ticker_data = data.reset_index()[["timestamp", "blockNumber", "operator", "trade_type", "value"]].copy()
    ticker_data.insert(2, "username", usernames.values.tolist())
    ticker_data.columns = ["Timestamp", "Block", "User", "Wallet", "Method", "Amount"]
    # Shorten wallet address string
    ticker_data["Wallet"] = ticker_data["Wallet"].str[:6] + "..." + ticker_data["Wallet"].str[-4:]
    ticker_data = ticker_data.set_index("Timestamp").sort_index(ascending=False)
    return ticker_data


def combine_usernames(username: pd.Series) -> pd.DataFrame:
    """Given a series of usernames, map them to a single user (e.g., click with bots)"""
    # Hard coded mapping:
    user_mapping = {
        "Charles St. Louis (click)": "Charles St. Louis",
        "Alim Khamisa (click)": "Alim Khamisa",
        "Danny Delott (click)": "Danny Delott",
        "Gregory Lisa (click)": "Gregory Lisa",
        "Jonny Rhea (click)": "Jonny Rhea",
        "Matt Brown (click)": "Matt Brown",
        "Giovanni Effio (click)": "Giovanni Effio",
        "Mihai Cosma (click)": "Mihai Cosma",
        "Ryan Goree (click)": "Ryan Goree",
        "Alex Towle (click)": "Alex Towle",
        "Adelina Ruffolo (click)": "Adelina Ruffolo",
        "Jacob Arruda (click)": "Jacob Arruda",
        "Dylan Paiton (click)": "Dylan Paiton",
        "Sheng Lundquist (click)": "Sheng Lundquist",
        "ControlC Schmidt (click)": "ControlC Schmidt",
        "George Towle (click)": "George Towle",
        "Jack Burrus (click)": "Jack Burrus",
        # Bot accounts
        "slundquist (bots)": "Sheng Lundquist",
    }
    user_mapping = pd.DataFrame.from_dict(user_mapping, orient="index")
    user_mapping.columns = ["user"]
    # Use merge in case mapping doesn't exist
    username_column = username.name
    user = username.to_frame().merge(user_mapping, how="left", left_on=username_column, right_index=True)
    return user


def get_leaderboard(pnl: pd.Series, lookup: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Given PNL, does lookup against usernames and ranks the leaderboard"""
    pnl = pnl.reset_index()  # type: ignore
    usernames = username_to_address(lookup, pnl["walletAddress"])
    pnl.insert(1, "username", usernames.values.tolist())
    # Hard coded funding provider from migration account
    migration_addr = "0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266"
    # Don't show this account
    pnl = pnl[pnl["walletAddress"] != migration_addr]
    # Rank based on pnl
    user = combine_usernames(pnl["username"])
    pnl["user"] = user["user"].values

    ind_leaderboard = (
        pnl[["username", "walletAddress", "pnl"]]
        .sort_values("pnl", ascending=False)  # type: ignore
        .reset_index(drop=True)
    )
    comb_leaderboard = (
        pnl[["user", "pnl"]].groupby("user")["pnl"].sum().reset_index().sort_values("pnl", ascending=False)
    ).reset_index(drop=True)

    return (comb_leaderboard, ind_leaderboard)


def get_click_addresses() -> pd.DataFrame:
    """Returns a dataframe of hard coded click addresses"""
    addresses = {
        "0x004dfC2dBA6573fa4dFb1E86e3723e1070C0CfdE": "Charles St. Louis (click)",
        "0x005182C62DA59Ff202D53d6E42Cef6585eBF9617": "Alim Khamisa (click)",
        "0x005BB73FddB8CE049eE366b50d2f48763E9Dc0De": "Danny Delott (click)",
        "0x0065291E64E40FF740aE833BE2F68F536A742b70": "Gregory Lisa (click)",
        "0x0076b154e60BF0E9088FcebAAbd4A778deC5ce2c": "Jonny Rhea (click)",
        "0x00860d89A40a5B4835a3d498fC1052De04996de6": "Matt Brown (click)",
        "0x00905A77Dc202e618d15d1a04Bc340820F99d7C4": "Giovanni Effio (click)",
        "0x009ef846DcbaA903464635B0dF2574CBEE66caDd": "Mihai Cosma (click)",
        "0x00D5E029aFCE62738fa01EdCA21c9A4bAeabd434": "Ryan Goree (click)",
        "0x020A6F562884395A7dA2be0b607Bf824546699e2": "Alex Towle (click)",
        "0x020a898437E9c9DCdF3c2ffdDB94E759C0DAdFB6": "Adelina Ruffolo (click)",
        "0x020b42c1E3665d14275E2823bCef737015c7f787": "Jacob Arruda (click)",
        "0x02147558D39cE51e19de3A2E1e5b7c8ff2778829": "Dylan Paiton (click)",
        "0x021f1Bbd2Ec870FB150bBCAdaaA1F85DFd72407C": "Sheng Lundquist (click)",
        "0x02237E07b7Ac07A17E1bdEc720722cb568f22840": "ControlC Schmidt (click)",
        "0x022ca016Dc7af612e9A8c5c0e344585De53E9667": "George Towle (click)",
        "0x0235037B42b4c0575c2575D50D700dD558098b78": "Jack Burrus (click)",
    }
    addresses = pd.DataFrame.from_dict(addresses, orient="index")
    addresses = addresses.reset_index()
    addresses.columns = ["address", "username"]

    return addresses


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
    # Usernames in postgres are bots
    user_map["username"] = user_map["username"] + " (bots)"

    click_map = get_click_addresses()
    user_map = pd.concat([click_map, user_map], axis=0)

    # Generate a lookup of users -> address, taking into account that some addresses don't have users
    # Reindex looks up agent addresses against user_map, adding nans if it doesn't exist
    options_map = user_map.set_index("address").reindex(agents)

    # Set username as address if agent doesn't exist
    na_idx = options_map["username"].isna()
    # If there are any nan usernames, set address itself as username
    if na_idx.any():
        options_map[na_idx] = options_map.index[na_idx]
    return options_map.reset_index()


def username_to_address(lookup: pd.DataFrame, selected_list: pd.Series) -> pd.Series:
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
    selected_list_column = selected_list.name
    out = selected_list.to_frame().merge(lookup, how="left", left_on=selected_list_column, right_on="address")
    return out["username"]


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
    user_lookup = get_user_lookup()
    txn_data = postgres.get_transactions(session, -max_live_blocks)
    pool_info_data = postgres.get_pool_info(session, -max_live_blocks)
    combined_data = get_combined_data(txn_data, pool_info_data)
    ticker = get_ticker(combined_data, user_lookup)
    wallets = postgres.get_current_wallet_info(session)

    (fixed_rate_x, fixed_rate_y) = calc_fixed_rate(combined_data, config_data)
    ohlcv = calc_ohlcv(combined_data, config_data, freq="5T")

    curr_pnl = calculate_current_pnl(config_data, pool_info_data, wallets)
    comb_rank, ind_rank = get_leaderboard(curr_pnl, user_lookup)

    with ticker_placeholder.container():
        st.header("Ticker")
        st.dataframe(ticker, height=200, use_container_width=True)
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

## Set up agent selection state list outside of live updates
# st.session_state.options = []
#
#
## Initialize select options for filtering
# user_lookup = get_user_lookup()
# if "agent_list" not in st.session_state:
#    st.session_state["agent_list"] = user_lookup["username"].unique().tolist()
# if "selected_agents" not in st.session_state:
#    st.session_state["selected_agents"] = []
# if "all_checkbox" not in st.session_state:
#    st.session_state.all_checkbox = False
#
# st.session_state.selected_agents = st.multiselect("PNL Agents", st.session_state.agent_list, key="agent_select")
## All checkbox
# st.session_state.all_checkbox = st.checkbox("View all", value=True)

# TODO Seperate out these figures
# TODO abstract out creating a streamlit container + adding a figure

## Initialize streamlit containers for display
# main_placeholder = st.empty()
# lp_plot_placeholder = st.empty()
#
# fig = mpf.figure(style="mike", figsize=(15, 15))  # type: ignore
# ax_ohlcv = fig.add_subplot(2, 2, 1)
# ax_fixed_rate = fig.add_subplot(2, 2, 2)
# ax_vol = fig.add_subplot(2, 2, 3)
# ax_pnl = fig.add_subplot(2, 2, 4)
#
# lp_fig = mpf.figure(style="mike", figsize=(10, 10))  # type: ignore
# ax_lp_token = lp_fig.add_subplot(1, 1, 1)
# lp_fig.set_tight_layout(True)  # type: ignore


## Main data loop
# while True:
#    print("collecting data")
#    pool_config_data = postgres.get_pool_config(session)
#    txn_data = postgres.get_transactions(session, start_block=start_block)
#    pool_info_data = postgres.get_pool_info(session, start_block=start_block)
#    checkpoint_info = postgres.get_checkpoint_info(session, start_block=start_block)
#    print("getting agent positions")
#    if st.session_state.all_checkbox:
#        agent_positions = postgres.get_agent_positions(session)
#    else:
#        selected_addrs = username_to_address(user_lookup, st.session_state.selected_agents)
#        agent_positions = postgres.get_agent_positions(session, selected_addrs)
#
#    # No data, wait
#    if len(pool_info_data) == 0 or len(txn_data) == 0:
#        time.sleep(0.1)
#        continue
#
#    # truncate the length of pool_info_data and checkpoint_info to the shorter of their two indexes.
#    latest_block = min(max(pool_info_data.index), max(checkpoint_info.index))
#    pool_info_data = pool_info_data.loc[:latest_block, :]
#    checkpoint_info = checkpoint_info.loc[:latest_block, :]
#    print("getting combined data")
#    combined_data = get_combined_data(txn_data, pool_info_data)
#
#    # Calculate data
#    print("calculating ohlcv")
#    ohlcv = calc_ohlcv(combined_data, freq="5T")
#    print("calculating fixed rate")
#    (fixed_rate_x, fixed_rate_y) = calc_fixed_rate(combined_data)
#    print("calculating pnl")
#    all_agent_info = calculate_pnl(pool_config_data, pool_info_data, checkpoint_info, agent_positions)
#    print("getting ticker")
#    ticker = get_ticker(txn_data)
#
#    # Place data and plots
#    with sidebar_placeholder.container():
#        st.dataframe(ticker.iloc[:100], height=900, use_container_width=True)
#
#    with main_placeholder.container():
#        # Clears all axes
#        ax_vol.clear()
#        ax_pnl.clear()
#        ax_ohlcv.clear()
#        ax_fixed_rate.clear()
#
#        plot_ohlcv(ohlcv, ax_ohlcv, ax_vol)
#        plot_fixed_rate(fixed_rate_x, fixed_rate_y, ax_fixed_rate)
#        plot_pnl(all_agent_info, ax_pnl)
#
#        # Fix axes labels
#        fig.autofmt_xdate()  # type: ignore
#        st.pyplot(fig=fig)  # type: ignore
#
#    with lp_plot_placeholder.container():
#        ax_lp_token.clear()
#        # TODO extract this out
#        num_lp_tokens = [ap.positions.loc[:, "LP"] for ap in agent_positions.values() if "LP" in ap.positions.columns]
#        addrs = [addr for addr, ap in agent_positions.items() if "LP" in ap.positions.columns]
#        if len(num_lp_tokens) > 0:
#            lp_data = pd.concat(num_lp_tokens, axis=1)
#            lp_data.columns = addrs
#            lp_data["lpTotalSupply"] = pool_info_data["lpTotalSupply"]
#        else:
#            lp_data = pool_info_data["lpTotalSupply"].to_frame()
#
#        ax_lp_token.plot(lp_data.sort_index(), label=lp_data.columns)
#        ax_lp_token.legend()
#        ax_lp_token.set_xlabel("block number")
#        ax_lp_token.set_ylabel("Number LP tokens")
#        ax_lp_token.set_title("LP Tokens over blocks")
#        st.pyplot(fig=lp_fig)  # type: ignore
#
#    time.sleep(0.1)
#
