"""Builds the leaderboard for the dashboard."""
import pandas as pd

from .usernames import address_to_username, combine_usernames


def build_leaderboard(wallet_pnl: pd.Series, lookup: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank users by PNL, individually and bomined across their accounts."""
    total_pnl = wallet_pnl.groupby("walletAddress")["pnl"].sum().reset_index()

    usernames = address_to_username(lookup, total_pnl["walletAddress"])
    total_pnl.insert(1, "username", usernames.values.tolist())

    # Rank based on pnl
    user = combine_usernames(total_pnl["username"])
    total_pnl["user"] = user["user"].values

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
