"""Builds the dataframes used by the dashboard."""

from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from agent0.chainsync.db.base import get_addr_to_username
from agent0.chainsync.db.hyperdrive import (
    get_all_traders,
    get_hyperdrive_addr_to_name,
    get_pool_info,
    get_position_snapshot,
    get_positions_over_time,
    get_realized_value_over_time,
    get_total_pnl_over_time,
    get_trade_events,
)

from .build_fixed_rate import build_fixed_rate
from .build_leaderboard import build_per_pool_leaderboard, build_total_leaderboard
from .build_ohlcv import build_ohlcv
from .build_outstanding_positions import build_outstanding_positions
from .build_ticker import build_ticker_for_pool_page, build_ticker_for_wallet_page
from .build_variable_rate import build_variable_rate
from .build_wallet_positions import (
    build_pnl_over_time,
    build_positions_over_time,
    build_realized_value_over_time,
    build_wallet_positions,
)
from .usernames import build_user_mapping


def build_pool_dashboard(
    hyperdrive_address: str, session: Session, max_live_blocks: int = 5000, max_ticker_rows: int = 1000
) -> dict[str, pd.DataFrame]:
    """Builds the dataframes for the main dashboard page that focuses on pools.

    Arguments
    ---------
    hyperdrive_address: str
        The hyperdrive address to filter the results on.
    session: Session
        The initialized sqlalchemy db session object.
    max_live_blocks: int, optional
        The maximum look-back length in blocks. Defaults to 5000.
    max_ticker_rows: int, optional
        The maximum number of ticker rows to show. Defaults to 1000.

    Returns
    -------
    dict[str, DataFrame]
        A collection of dataframes ready to be shown in the dashboard.
    """

    out_dfs: dict[str, pd.DataFrame] = {}

    freq = None
    # Wallet addr to username mapping
    trader_addrs = get_all_traders(session, hyperdrive_address=hyperdrive_address)
    addr_to_username = get_addr_to_username(session)
    user_map = build_user_mapping(trader_addrs, addr_to_username)

    pool_info = get_pool_info(
        session, hyperdrive_address=hyperdrive_address, start_block=-max_live_blocks, coerce_float=False
    )

    # Get a block to timestamp mapping dataframe
    block_to_timestamp = pool_info[["block_number", "timestamp"]]

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

    # TODO these trade events won't show the token delta for withdrawal shares
    # for RemoveLiquidity
    trade_events = get_trade_events(
        session,
        hyperdrive_address=hyperdrive_address,
        all_token_deltas=False,
        sort_ascending=False,  # We want the latest first in a ticker
        query_limit=max_ticker_rows,
        coerce_float=False,
    )
    # Adds user lookup to the ticker
    out_dfs["display_ticker"] = build_ticker_for_pool_page(trade_events, user_map, block_to_timestamp)

    # Since this table is updated every block, we try and lag behind one block
    # for position snapshots to avoid getting a currently updating block.
    latest_wallet_pnl = get_position_snapshot(
        session,
        hyperdrive_address=hyperdrive_address,
        start_block=-1,
        end_block=None,
        coerce_float=False,
    )
    out_dfs["leaderboard"] = build_total_leaderboard(latest_wallet_pnl, user_map)

    # build ohlcv and volume
    out_dfs["ohlcv"] = build_ohlcv(pool_info, freq=freq)
    # build rates
    out_dfs["fixed_rate"] = build_fixed_rate(pool_info)
    out_dfs["variable_rate"] = build_variable_rate(pool_info)

    # build outstanding positions plots
    out_dfs["outstanding_positions"] = build_outstanding_positions(pool_info)

    return out_dfs


def build_wallet_dashboard(
    wallet_addresses: list[str],
    session: Session,
    user_map: pd.DataFrame | None = None,
    max_plot_blocks: int = 5000,
    max_ticker_rows: int = 1000,
) -> dict[str, pd.DataFrame]:
    """Builds the dataframes for the main dashboard page that focuses on pools.

    Arguments
    ---------
    wallet_addresses: list[str]
        The list of wallet addresses to filter the results on.
    session: Session
        The initialized sqlalchemy db session object.
    user_map: pd.DataFrame | None, optional
        The mapping of wallet addresses to usernames. Will build from db if None.
    max_plot_blocks: int, optional
        The maximum number of blocks to look in the past for plotting. Defaults to 5000.
    max_ticker_rows: int, optional
        The maximum number of ticker rows to show. Defaults to 1000.

    Returns
    -------
    dict[str, DataFrame]
        A collection of dataframes ready to be shown in the dashboard.
    """

    # pylint: disable=too-many-locals

    if user_map is None:
        trader_addrs = get_all_traders(session)
        addr_to_username = get_addr_to_username(session)
        # Get corresponding usernames
        user_map = build_user_mapping(trader_addrs, addr_to_username)

    hyperdrive_addr_mapping = get_hyperdrive_addr_to_name(session)
    # Get ticker for selected addresses
    out_dfs: dict[str, pd.DataFrame] = {}

    pool_info = get_pool_info(session, start_block=-max_plot_blocks, coerce_float=False)
    # Get a block to timestamp mapping dataframe
    # Since we're getting this from multiple addrs, we drop duplicates
    # TODO get this table directly from a db query
    block_to_timestamp = pool_info[["block_number", "timestamp"]].drop_duplicates(ignore_index=True)

    # TODO these trade events won't show the token delta for withdrawal shares
    # for RemoveLiquidity
    trade_events = get_trade_events(
        session,
        wallet_address=wallet_addresses,
        all_token_deltas=False,
        sort_ascending=False,
        query_limit=max_ticker_rows,
        coerce_float=False,
    )
    # Adds user lookup to the ticker
    out_dfs["display_ticker"] = build_ticker_for_wallet_page(
        trade_events, user_map, hyperdrive_addr_mapping, block_to_timestamp
    )

    # Since this table is updated every block, we try and lag behind one block
    # for position snapshots to avoid getting a currently updating block.
    position_snapshot = get_position_snapshot(
        session,
        wallet_address=wallet_addresses,
        start_block=-1,
        end_block=None,
        coerce_float=False,
    )

    # Pnl aggregation
    out_dfs["total_pnl"] = build_total_leaderboard(
        position_snapshot,
        user_map=user_map,
    )
    out_dfs["pool_pnl"] = build_per_pool_leaderboard(
        position_snapshot,
        user_map=user_map,
        hyperdrive_addr_map=hyperdrive_addr_mapping,
    )

    # Current positions
    current_positions = build_wallet_positions(
        position_snapshot,
        user_map=user_map,
        hyperdrive_addr_map=hyperdrive_addr_mapping,
    )

    # Split up into open and closed positions
    out_dfs["open_positions"] = (
        current_positions[current_positions["Token Balance"] != 0].reset_index(drop=True).astype(str)
    )
    out_dfs["closed_positions"] = (
        current_positions[current_positions["Token Balance"] == 0].reset_index(drop=True).astype(str)
    )

    pnl_over_time = get_total_pnl_over_time(
        session, wallet_address=wallet_addresses, start_block=-max_plot_blocks, coerce_float=True
    )

    out_dfs["pnl_over_time"] = build_pnl_over_time(pnl_over_time, block_to_timestamp)

    # Get positions over time
    wallet_positions_over_time = get_positions_over_time(
        session, wallet_address=wallet_addresses, start_block=-max_plot_blocks, coerce_float=True
    )
    out_dfs["positions_over_time"] = build_positions_over_time(wallet_positions_over_time, block_to_timestamp)

    realized_value_over_time = get_realized_value_over_time(
        session, wallet_address=wallet_addresses, start_block=-max_plot_blocks, coerce_float=True
    )
    out_dfs["realized_value_over_time"] = build_realized_value_over_time(realized_value_over_time, block_to_timestamp)

    return out_dfs
