"""Builds the ticker for the dashboard."""

import pandas as pd

from .usernames import abbreviate_address, map_addresses


def build_ticker_for_pool_page(
    trade_events: pd.DataFrame, user_map: pd.DataFrame, block_to_timestamp: pd.DataFrame
) -> pd.DataFrame:
    """Builds the ticker dataframe for the pool page.

    Arguments
    ---------
    trade_events: pd.DataFrame
        The dataframe resulting from `get_trade_events`.
    user_map: pd.DataFrame
        A dataframe containing the mapping of wallet addresses to usernames.
    block_to_timestamp: pd.DataFrame
        A dataframe containing the mapping of block number to timestamp.

    Returns
    -------
    pd.DataFrame
        The filtered transaction data based on what we want to view in the ticker for a specific pool.
    """
    # Gather other information from other tables
    mapped_addrs = map_addresses(trade_events["wallet_address"], user_map)

    trade_events = trade_events.copy()
    trade_events["username"] = mapped_addrs["username"]

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
        "vault_share_delta": "Vault Share Change",
    }
    trade_events = trade_events[list(rename_dict.keys())].rename(columns=rename_dict)

    # Shorten wallet address string
    trade_events["Wallet"] = mapped_addrs["abbr_address"]
    return trade_events


def build_ticker_for_wallet_page(
    trade_events: pd.DataFrame,
    user_map: pd.DataFrame,
    hyperdrive_addr_map: pd.DataFrame,
    block_to_timestamp: pd.DataFrame,
) -> pd.DataFrame:
    """Builds the ticker dataframe for the wallet page.

    Arguments
    ---------
    trade_events: pd.DataFrame
        The dataframe resulting from `get_trade_events`.
    user_map: pd.DataFrame
        A dataframe containing the mapping of wallet addresses to usernames.
    hyperdrive_addr_map: pd.DataFrame
        A dataframe containing the mapping of hyperdrive addresses to hyperdrive names.
    block_to_timestamp: pd.DataFrame
        A dataframe containing the mapping of block number to timestamp.

    Returns
    -------
    pd.DataFrame
        The filtered transaction data based on what we want to view in the ticker for a specific wallet.
    """

    mapped_addrs = map_addresses(trade_events["wallet_address"], user_map)
    trade_events = trade_events.copy()
    trade_events["username"] = mapped_addrs["username"]

    # Do lookup from address to name
    hyperdrive_name = (
        trade_events["hyperdrive_address"]
        .to_frame()
        .merge(hyperdrive_addr_map, how="left", left_on="hyperdrive_address", right_on="hyperdrive_address")
    )["name"]

    trade_events["hyperdrive_name"] = hyperdrive_name

    # Look up block to timestamp
    trade_events = trade_events.merge(block_to_timestamp, how="left", on="block_number")

    rename_dict = {
        "timestamp": "Timestamp",
        "block_number": "Block Number",
        "hyperdrive_name": "Hyperdrive Name",
        "hyperdrive_address": "Hyperdrive Address",
        "username": "User",
        "wallet_address": "Wallet",
        "event_type": "Trade",
        "token_id": "Token",
        "token_delta": "Token Change",
        "base_delta": "Base Change",
        "vault_share_delta": "Vault Share Change",
    }
    trade_events = trade_events[list(rename_dict.keys())].rename(columns=rename_dict)

    # Shorten wallet address string
    trade_events["Wallet"] = mapped_addrs["abbr_address"]
    trade_events["Hyperdrive Address"] = abbreviate_address(trade_events["Hyperdrive Address"])

    # Sort latest first
    return trade_events
