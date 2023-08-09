"""Builds the ticker for the dashboard."""
import pandas as pd

from .usernames import address_to_username


def build_ticker(
    wallet_delta: pd.DataFrame, transactions: pd.DataFrame, pool_info: pd.DataFrame, lookup: pd.DataFrame
) -> pd.DataFrame:
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
    # TODO these merges should really happen via an sql query instead of in pandas here
    # Set ticker so that each transaction is a single row
    ticker_data = wallet_delta.groupby(["transactionHash"]).agg(
        {"blockNumber": "first", "walletAddress": "first", "baseTokenType": tuple, "delta": tuple}
    )

    # Expand column of lists into seperate dataframes, then str cat them together
    token_type = pd.DataFrame(ticker_data["baseTokenType"].to_list(), index=ticker_data.index)
    token_deltas = pd.DataFrame(ticker_data["delta"].to_list(), index=ticker_data.index)
    token_diffs = token_type + ": " + token_deltas.astype("str")
    # Aggregate columns into a single list, removing nans
    token_diffs = token_diffs.stack().groupby(level=0).agg(list)

    # Gather other information from other tables
    usernames = address_to_username(lookup, ticker_data["walletAddress"])
    timestamps = pool_info.loc[ticker_data["blockNumber"], "timestamp"]
    trade_type = transactions.set_index("transactionHash").loc[ticker_data.index, "input_method"]

    ticker_data = ticker_data[["blockNumber", "walletAddress"]].copy()
    ticker_data.insert(0, "timestamp", timestamps.values)  # type: ignore
    ticker_data.insert(2, "username", usernames.values)  # type: ignore
    ticker_data.insert(4, "trade_type", trade_type)
    ticker_data.insert(5, "token_diffs", token_diffs)  # type: ignore
    ticker_data.columns = ["Timestamp", "Block", "User", "Wallet", "Method", "Token Deltas"]
    # Shorten wallet address string
    ticker_data["Wallet"] = ticker_data["Wallet"].str[:6] + "..." + ticker_data["Wallet"].str[-4:]
    # Return reverse of methods to put most recent transactions at the top
    ticker_data = ticker_data.set_index("Timestamp").sort_index(ascending=False)
    # Drop rows with nonexistant wallets
    ticker_data = ticker_data.dropna(axis=0, subset="Wallet")
    return ticker_data
