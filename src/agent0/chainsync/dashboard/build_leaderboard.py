"""Builds the leaderboard for the dashboard."""

import pandas as pd

from .usernames import map_addresses


def build_leaderboard(position_snapshot: pd.DataFrame, user_map: pd.DataFrame) -> pd.DataFrame:
    """Rank users by PNL, individually and bomined across their accounts.

    Arguments
    ---------
    wallet_pnl: pd.DataFrame
        The dataframe resulting from get_wallet_pnl.
    user_map: pd.DataFrame
        A dataframe with 4 columns (address, abbr_address, username, format_name).
        This is the output of :meth:`chainsync.dashboard.build_user_mapping`.

    Returns
    -------
    tuple[pd.DataFrame, pd.DataFrame]
        The user-combined and individual wallet leaderboard dataframes.
    """
    total_pnl = position_snapshot.groupby("wallet_address")["pnl"].sum().reset_index()

    mapped_addrs = map_addresses(total_pnl["wallet_address"], user_map)
    total_pnl.insert(1, "username", mapped_addrs["username"])

    # Rank based on pnl
    leaderboard = (
        total_pnl[["username", "wallet_address", "pnl"]]
        .sort_values("pnl", ascending=False)  # type: ignore
        .reset_index(drop=True)
    )

    leaderboard.index.name = "rank"

    # Convert these leaderboards to strings, as streamlit doesn't like decimals
    return leaderboard.astype(str)
