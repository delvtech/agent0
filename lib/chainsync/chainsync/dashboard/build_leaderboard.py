"""Builds the leaderboard for the dashboard."""
import pandas as pd

from .usernames import map_addresses


def build_leaderboard(wallet_pnl: pd.DataFrame, user_map: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank users by PNL, individually and bomined across their accounts."""
    total_pnl = wallet_pnl.groupby("walletAddress")["pnl"].sum().reset_index()

    mapped_addrs = map_addresses(total_pnl["walletAddress"], user_map)
    total_pnl.insert(1, "username", mapped_addrs["usernames"])
    total_pnl["user"] = mapped_addrs["user"]

    # Rank based on pnl
    ind_leaderboard = (
        total_pnl[["username", "walletAddress", "pnl"]]
        .sort_values("pnl", ascending=False)  # type: ignore
        .reset_index(drop=True)
    )
    comb_leaderboard = (
        total_pnl[["user", "pnl"]].groupby("user")["pnl"].sum().reset_index().sort_values("pnl", ascending=False)
    ).reset_index(drop=True)

    ind_leaderboard.index.name = "rank"
    comb_leaderboard.index.name = "rank"

    # Convert these leaderboards to strings, as streamlit doesn't like decimals
    return (comb_leaderboard.astype(str), ind_leaderboard.astype(str))
