"""
Utilities for extracting data from logs
"""

from __future__ import annotations
import json
import time
import numpy as np
import pandas as pd

from elfpy.markets.hyperdrive import hyperdrive_assets
from elfpy.markets.hyperdrive import AssetIdPrefix


def read_json_to_pd(json_file):
    """
    Generic function to read json file path to pandas dataframe
    """
    # Avoids race condition if background process is writing, keep trying until it passes
    while True:
        try:
            with open(json_file, mode="r", encoding="UTF-8") as file:
                json_data = json.load(file)
            break
        except json.JSONDecodeError:
            time.sleep(0.1)
            continue
    return pd.DataFrame(json_data)


def explode_transaction_data(data):
    """
    Extract transaction dataframe column to dataframe
    """

    assert len(data["transaction"]) == len(data["logs"])
    assert len(data["logs"]) == len(data["receipt"])

    # Expand logs while keeping original index
    log_data = data["logs"].reset_index().explode("logs")
    log_idxs = log_data["index"]
    log_data = pd.json_normalize(log_data["logs"])
    log_data["index"] = log_idxs.values
    # Reindex exploded data, index column keeps track of idx in original data
    log_data = log_data.reset_index(drop=True)

    # We're only interested in TransferSingle
    log_data = log_data[log_data["event"] == "TransferSingle"]
    log_data = log_data.set_index("index")
    transaction_data = pd.json_normalize(data["transaction"])
    # Drop logs here, we have decoded logs in data["logs"]
    receipt_data = pd.json_normalize(data["receipt"]).drop(["logs"], axis=1)

    # Concatenate all three columns into one dataframe
    # Note that concat will take into account index of all 3 dfs
    # so log_data will map to the other two dfs
    cat_data = pd.concat([transaction_data, log_data, receipt_data], axis=1)

    # Drop duplicate columns here, will keep first one
    cat_data = cat_data.loc[:, ~cat_data.columns.duplicated(keep="first")].copy()

    return cat_data


def calculate_spot_price(
    share_reserves,
    bond_reserves,
    lp_total_supply,
    maturity_timestamp=1.0,
    block_timestamp=0.0,
    position_duration=1.0,
):
    """Calculates the spot price given the pool info data"""
    # pylint: disable=too-many-arguments

    # Hard coding variables to calculate spot price
    initial_share_price = 1
    time_remaining_stretched = 0.045071688063194093
    full_term_spot_price = (
        (initial_share_price * (share_reserves / 1e18)) / ((bond_reserves / 1e18) + (lp_total_supply / 1e18))
    ) ** time_remaining_stretched

    time_left_in_years = (maturity_timestamp - block_timestamp) / position_duration

    return full_term_spot_price * time_left_in_years + 1 * (1 - time_left_in_years)


def get_combined_data(txn_data, pool_info_data):
    """
    Takes the transaction data nad pool info data and
    combines the two dataframes into a single dataframe
    """
    pool_info_data.index = pool_info_data.index.astype(int)
    # txn_data.index = txn_data["blockNumber"]
    # Combine pool info data and trans data by block number
    data = txn_data.merge(pool_info_data)
    data["timestamp"] = data["timestamp"].astype(int)

    rename_dict = {
        "args.operator": "operator",
        "args.from": "from",
        "args.to": "to",
        "args.id": "id",
        "args.value": "value",
        "bondReserves": "bond_reserves",
        "blockNumber": "block_number",
        "blockHash": "block_hash",
        "contractAddress": "contract_address",
        "input.method": "trade_type",
        "longsOutstanding": "longs_outstanding",
        "longAverageMaturityTime": "longs_average_maturity_time",
        "lpTotalSupply": "lp_total_supply",
        "sharePrice": "share_price",
        "shareReserves": "share_reserves",
        "shortAverageMaturityTime": "short_average_maturity_time",
        "shortBaseVolume": "short_base_volume",
        "shortsOutstanding": "shorts_outstanding",
        "timestamp": "block_timestamp",
        "transactionHash": "transaction_hash",
        "transactionIndex": "transaction_index",
    }

    # %%
    # Filter data based on columns
    trade_data = data[list(rename_dict)]
    # Rename columns
    trade_data = trade_data.rename(columns=rename_dict)

    # FIXME: Fix this -- will break if we allow multiple trades per block
    trade_data.index = trade_data["block_number"]

    # Calculate trade type and timetsamp from args.id

    def decode_id(row):
        # Check for nans
        # pylint disable=comparison-with-itself
        if row["id"] != row["id"]:
            out = (np.nan, np.nan)
        else:
            out = hyperdrive_assets.decode_asset_id(int(row["id"]))
        return out

    def decode_prefix(row):
        # Check for nans
        if np.isnan(row):
            out = np.nan
        else:
            out = AssetIdPrefix(row).name
        return out

    tuple_series = trade_data.apply(func=decode_id, axis=1)
    prefix, maturity_time = zip(*tuple_series)
    trade_data["prefix"] = prefix
    trade_data["maturity_timestamp"] = maturity_time

    trade_data["trade_enum"] = trade_data["prefix"].apply(decode_prefix)

    return trade_data
