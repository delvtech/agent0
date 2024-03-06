"""Calculates a ticker based on wallet deltas"""

import pandas as pd


def calc_ticker(wallet_delta: pd.DataFrame, transactions: pd.DataFrame, pool_info: pd.DataFrame) -> pd.DataFrame:
    """Adjusts wallet_deltas to be a ticker with one row per transaction.

    Arguments
    ---------
    wallet_delta: pd.DataFrame
        The dataframe resulting from `get_wallet_deltas`
    transactions: pd.DataFrame
        The dataframe resulting from `get_transactions`
    pool_info: pd.DataFrame
        The dataframe resulting from `get_pool_info`

    Returns
    -------
    pd.DataFrame
        The calculated ticker dataframe
    """
    # TODO these merges should really happen via an sql query instead of in pandas here
    # Set ticker so that each transaction is a single row
    ticker_data = wallet_delta.groupby(["transaction_hash"]).agg(
        {"block_number": "first", "wallet_address": "first", "base_token_type": tuple, "delta": tuple}
    )

    # Expand column of lists into separate dataframes, then str cat them together
    token_type = pd.DataFrame(ticker_data["base_token_type"].to_list(), index=ticker_data.index)
    token_deltas = pd.DataFrame(ticker_data["delta"].to_list(), index=ticker_data.index)
    token_diffs = token_type + ": " + token_deltas.astype("str")
    # Aggregate columns into a single list, removing nans
    token_diffs = token_diffs.stack().groupby(level=0).agg(list)

    # Gather other information from other tables
    timestamps = pool_info.set_index("block_number").loc[ticker_data["block_number"], "timestamp"]
    trade_type = transactions.set_index("transaction_hash").loc[ticker_data.index, "input_method"]

    ticker_data = ticker_data[["block_number", "wallet_address"]].copy()
    ticker_data["timestamp"] = timestamps.values
    ticker_data["trade_type"] = trade_type
    ticker_data["token_diffs"] = token_diffs
    # Drop rows with nonexistent wallets
    ticker_data = ticker_data.dropna(axis=0, subset="wallet_address")
    # Remove txn hash index and sort by block_number
    ticker_data = ticker_data.sort_values("block_number").reset_index(drop=True)
    return ticker_data
