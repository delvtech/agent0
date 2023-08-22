"""Calculates a ticker based on wallet deltas"""
import pandas as pd


def calc_ticker(wallet_delta: pd.DataFrame, transactions: pd.DataFrame, pool_info: pd.DataFrame) -> pd.DataFrame:
    """Adjusts wallet_deltas to be a ticker with one row per transaction"""
    # TODO these merges should really happen via an sql query instead of in pandas here
    # Set ticker so that each transaction is a single row
    ticker_data = wallet_delta.groupby(["transactionHash"]).agg(
        {"blockNumber": "first", "walletAddress": "first", "baseTokenType": tuple, "delta": tuple}
    )

    # Expand column of lists into separate dataframes, then str cat them together
    token_type = pd.DataFrame(ticker_data["baseTokenType"].to_list(), index=ticker_data.index)
    token_deltas = pd.DataFrame(ticker_data["delta"].to_list(), index=ticker_data.index)
    token_diffs = token_type + ": " + token_deltas.astype("str")
    # Aggregate columns into a single list, removing nans
    token_diffs = token_diffs.stack().groupby(level=0).agg(list)

    # Gather other information from other tables
    timestamps = pool_info.loc[ticker_data["blockNumber"], "timestamp"]
    trade_type = transactions.set_index("transactionHash").loc[ticker_data.index, "input_method"]

    ticker_data = ticker_data[["blockNumber", "walletAddress"]].copy()
    ticker_data["timestamp"] = timestamps.values
    ticker_data["trade_type"] = trade_type
    ticker_data["token_diffs"] = token_diffs
    # Drop rows with nonexistent wallets
    ticker_data = ticker_data.dropna(axis=0, subset="walletAddress")
    # Remove txn hash index and sort by blockNumber
    ticker_data = ticker_data.sort_values("blockNumber").reset_index(drop=True)
    return ticker_data
