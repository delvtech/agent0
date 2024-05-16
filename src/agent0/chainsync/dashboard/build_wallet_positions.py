import pandas as pd

from .usernames import abbreviate_address, map_addresses


def build_wallet_positions(
    positions_snapshot: pd.DataFrame,
    user_map: pd.DataFrame,
    hyperdrive_addr_map: pd.DataFrame,
) -> pd.DataFrame:
    """Show recent trades wrt a wallet.

    Arguments
    ---------
    trade_events: pd.DataFrame
        The dataframe resulting from `get_trade_events`.
    hyperdrive_addr_map: pd.DataFrame
        A dataframe with 2 columns (address, abbr_address, username, format_name).
        This is the output of :meth:`chainsync.dashboard.build_user_mapping`.

    Returns
    -------
    pd.DataFrame
        The filtered transaction data based on what we want to view in the ticker.
    """
    position_snapshot = positions_snapshot.copy()
    mapped_addrs = map_addresses(position_snapshot["wallet_address"], user_map)
    position_snapshot["username"] = mapped_addrs["username"]

    hyperdrive_name = (
        position_snapshot["hyperdrive_address"]
        .to_frame()
        .merge(hyperdrive_addr_map, how="left", left_on="hyperdrive_address", right_on="hyperdrive_address")
    )["name"]
    position_snapshot["hyperdrive_name"] = hyperdrive_name

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
    position_snapshot = position_snapshot[list(rename_dict.keys())].rename(columns=rename_dict)

    # Shorten wallet address string
    position_snapshot["Wallet"] = mapped_addrs["abbr_address"]
    position_snapshot["Hyperdrive Address"] = abbreviate_address(position_snapshot["Hyperdrive Address"])

    # Sort latest first
    return position_snapshot


def build_pnl_over_time(pnl_over_time: pd.DataFrame, block_to_timestamp: pd.DataFrame) -> pd.DataFrame:
    # Look up block to timestamp
    return pnl_over_time.merge(block_to_timestamp, how="left", on="block_number")


def build_positions_over_time(positions_over_time: pd.DataFrame, block_to_timestamp: pd.DataFrame) -> pd.DataFrame:
    return positions_over_time.merge(block_to_timestamp, how="left", on="block_number")


def build_realized_value_over_time(positions_over_time: pd.DataFrame, block_to_timestamp: pd.DataFrame) -> pd.DataFrame:
    return positions_over_time.merge(block_to_timestamp, how="left", on="block_number")
