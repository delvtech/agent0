"""Builds the ticker for the dashboard."""

import pandas as pd

from .usernames import map_addresses


def build_ticker(ticker_data: pd.DataFrame, user_map: pd.DataFrame) -> pd.DataFrame:
    """Show recent trades.

    Arguments
    ---------
    ticker_data: pd.DataFrame
        The dataframe resulting from get_transactions.
    user_map: pd.DataFrame
        A dataframe with 5 columns (address, abbr_address, username, user, format_name).
        This is the output of :meth:`chainsync.dashboard.build_user_mapping`.

    Returns
    -------
    pd.DataFrame
        The filtered transaction data based on what we want to view in the ticker.
    """
    # Gather other information from other tables
    mapped_addrs = map_addresses(ticker_data["wallet_address"], user_map)

    ticker_data = ticker_data.copy()
    ticker_data = ticker_data.drop("id", axis=1)
    ticker_data.insert(2, "username", mapped_addrs["username"])
    ticker_data.columns = ["Block Number", "Timestamp", "User", "Wallet", "Method", "Token Deltas"]
    # Shorten wallet address string
    ticker_data["Wallet"] = mapped_addrs["abbr_address"]
    # Drop rows with nonexistant wallets
    ticker_data = ticker_data.dropna(axis=0, subset="Wallet")
    return ticker_data
