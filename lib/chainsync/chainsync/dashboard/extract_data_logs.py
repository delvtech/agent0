"""Utilities for extracting data from logs."""

from __future__ import annotations

import json
import time

import numpy as np
import pandas as pd
from ethpy.hyperdrive import AssetIdPrefix


def read_json_to_pd(json_file):
    """Read json file path to pandas dataframe."""
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


def get_combined_data(txn_data, pool_info_data):
    """Combine multiple datasets into one containing transaction data, and pool info."""
    pool_info_data.index = pool_info_data.index.astype(int)
    # txn_data.index = txn_data["blockNumber"]
    # Combine pool info data and trans data by block number
    data = txn_data.merge(pool_info_data, on="blockNumber")

    rename_dict = {
        "event_operator": "operator",
        "event_from": "from",
        "event_to": "to",
        "event_id": "id",
        "event_prefix": "prefix",
        "event_maturity_time": "maturity_time",
        "event_value": "value",
        "bondReserves": "bond_reserves",
        "input_method": "trade_type",
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

    # Calculate trade type and timetsamp from args.id
    def decode_prefix(row):
        # Check for nans
        if np.isnan(row):
            out = np.nan
        else:
            out = AssetIdPrefix(row).name
        return out

    trade_data["trade_enum"] = trade_data["prefix"].apply(decode_prefix)
    trade_data["timestamp"] = trade_data["block_timestamp"]
    trade_data["block_timestamp"] = trade_data["block_timestamp"].astype(int)

    trade_data = trade_data.sort_values("block_timestamp")

    return trade_data
