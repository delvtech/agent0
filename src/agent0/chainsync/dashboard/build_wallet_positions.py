"""Builds the position dataframe for the dashboard."""

import pandas as pd

from .usernames import abbreviate_address, map_addresses


def build_wallet_positions(
    positions_snapshot: pd.DataFrame,
    user_map: pd.DataFrame,
    hyperdrive_addr_map: pd.DataFrame,
) -> pd.DataFrame:
    """Builds the positions dataframe for the wallet page.

    Arguments
    ---------
    positions_snapshot: pd.DataFrame
        The dataframe resulting from get_position_snapshot that contains the latest positions.
    user_map: pd.DataFrame
        A dataframe containing the mapping of wallet addresses to usernames.
    hyperdrive_addr_map: pd.DataFrame
        A dataframe containing the mapping of hyperdrive addresses to names.

    Returns
    -------
    pd.DataFrame
        The wallet positions dataframe for the dashboard.
    """
    positions_snapshot = positions_snapshot.copy()
    mapped_addrs = map_addresses(positions_snapshot["wallet_address"], user_map)
    positions_snapshot["username"] = mapped_addrs["username"]

    hyperdrive_name = (
        positions_snapshot["hyperdrive_address"]
        .to_frame()
        .merge(hyperdrive_addr_map, how="left", left_on="hyperdrive_address", right_on="hyperdrive_address")
    )["name"]
    positions_snapshot["hyperdrive_name"] = hyperdrive_name

    rename_dict = {
        "username": "Username",
        "wallet_address": "Wallet Address",
        "hyperdrive_name": "Hyperdrive Name",
        "hyperdrive_address": "Hyperdrive Address",
        "token_id": "Token",
        "token_balance": "Token Balance",
        "unrealized_value": "Unrealized Value",
        "realized_value": "Realized Value",
        "pnl": "PnL",
    }
    positions_snapshot = positions_snapshot[list(rename_dict.keys())].rename(columns=rename_dict)

    # Shorten wallet address string
    positions_snapshot["Wallet"] = mapped_addrs["abbr_address"]
    positions_snapshot["Hyperdrive Address"] = abbreviate_address(positions_snapshot["Hyperdrive Address"])

    return positions_snapshot


def build_pnl_over_time(pnl_over_time: pd.DataFrame, block_to_timestamp: pd.DataFrame) -> pd.DataFrame:
    """Builds the pnl over time dataframe for the dashboard.

    Arguments
    ---------
    pnl_over_time: pd.DataFrame
        The dataframe resulting from `get_pnl_over_time`.
    block_to_timestamp: pd.DataFrame
        A dataframe containing the mapping of block number to timestamp.

    Returns
    -------
    pd.DataFrame
        The pnl over time dataframe for the dashboard.
    """
    # Look up block to timestamp
    return pnl_over_time.merge(block_to_timestamp, how="left", on="block_number")


def build_positions_over_time(positions_over_time: pd.DataFrame, block_to_timestamp: pd.DataFrame) -> pd.DataFrame:
    """Builds the positions over time dataframe for the dashboard.

    Arguments
    ---------
    positions_over_time: pd.DataFrame
        The dataframe resulting from `get_positions_over_time`.
    block_to_timestamp: pd.DataFrame
        A dataframe containing the mapping of block number to timestamp.

    Returns
    -------
    pd.DataFrame
        The positions over time dataframe for the dashboard.
    """
    return positions_over_time.merge(block_to_timestamp, how="left", on="block_number")


def build_realized_value_over_time(
    realized_value_over_time: pd.DataFrame, block_to_timestamp: pd.DataFrame
) -> pd.DataFrame:
    """Builds the realized value over time dataframe for the dashboard.

    Arguments
    ---------
    realized_value_over_time: pd.DataFrame
        The dataframe resulting from `get_realized_value_over_time`.
    block_to_timestamp: pd.DataFrame
        A dataframe containing the mapping of block number to timestamp.

    Returns
    -------
    pd.DataFrame
        The realized value over time dataframe for the dashboard.
    """
    return realized_value_over_time.merge(block_to_timestamp, how="left", on="block_number")
