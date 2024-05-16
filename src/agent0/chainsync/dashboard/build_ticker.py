"""Builds the ticker for the dashboard."""

import pandas as pd

from .usernames import map_addresses


def build_ticker(trade_events: pd.DataFrame, user_map: pd.DataFrame, block_to_timestamp: pd.DataFrame) -> pd.DataFrame:
    """Show recent trades.

    Arguments
    ---------
    trade_events: pd.DataFrame
        The dataframe resulting from `get_trade_events`.
    user_map: pd.DataFrame
        A dataframe with 5 columns (address, abbr_address, username, user, format_name).
        This is the output of :meth:`chainsync.dashboard.build_user_mapping`.

    Returns
    -------
    pd.DataFrame
        The filtered transaction data based on what we want to view in the ticker.
    """
    # Gather other information from other tables
    mapped_addrs = map_addresses(trade_events["wallet_address"], user_map)

    trade_events = trade_events.copy()
    trade_events.insert(2, "username", mapped_addrs["username"])

    # Look up block to timestamp
    trade_events = trade_events.merge(block_to_timestamp, how="left", on="block_number")

    rename_dict = {
        "timestamp": "Timestamp",
        "block_number": "Block Number",
        "username": "User",
        "wallet_address": "Wallet",
        "event_type": "Trade",
        "token_id": "Token",
        "token_delta": "Token Change",
        "base_delta": "Base Change",
        "as_base": "As Base",
    }
    trade_events = trade_events[list(rename_dict.keys())].rename(columns=rename_dict)

    # Shorten wallet address string
    trade_events["Wallet"] = mapped_addrs["abbr_address"]
    return trade_events
