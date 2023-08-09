"""Builds the leaderboard for the dashboard."""
import pandas as pd

from .usernames import address_to_username, combine_usernames


def build_leaderboard(pnl: pd.Series, lookup: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank users by PNL, individually and bomined across their accounts."""
    pnl = pnl.reset_index()  # type: ignore
    usernames = address_to_username(lookup, pnl["walletAddress"])
    pnl.insert(1, "username", usernames.values.tolist())
    # TODO: Hard coded funding provider from migration account
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
