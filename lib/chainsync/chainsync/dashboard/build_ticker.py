"""Builds the ticker for the dashboard."""
import pandas as pd

from .usernames import address_to_username


def build_ticker(ticker_data: pd.DataFrame, lookup: pd.DataFrame) -> pd.DataFrame:
    """Show recent trades.

    Arguments
    ---------
    data: pd.DataFrame
        The dataframe resulting from get_transactions

    Returns
    -------
    pd.DataFrame
        The filtered transaction data based on what we want to view in the ticker
    """

    # Gather other information from other tables
    usernames = address_to_username(lookup, ticker_data["walletAddress"])

    ticker_data = ticker_data.copy()
    ticker_data = ticker_data.drop("id", axis=1)
    ticker_data.insert(2, "username", usernames.values)  # type: ignore
    ticker_data.columns = ["blockNumber", "Timestamp", "User", "Wallet", "Method", "Token Deltas"]
    # Shorten wallet address string
    ticker_data["Wallet"] = ticker_data["Wallet"].str[:6] + "..." + ticker_data["Wallet"].str[-4:]
    # Return reverse of methods to put most recent transactions at the top
    ticker_data = ticker_data.set_index("Timestamp").sort_index(ascending=False)
    # Drop rows with nonexistant wallets
    ticker_data = ticker_data.dropna(axis=0, subset="Wallet")
    return ticker_data
