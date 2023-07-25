"""Utilities for extracting data from logs."""

from __future__ import annotations

import json
import logging
import time

import numpy as np
import pandas as pd

from elfpy.hyperdrive_interface import AssetIdPrefix


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


def calculate_spot_price_from_state(state, maturity_timestamp, block_timestamp, pool_config):
    """Calculate spot price from reserves stored in a state variable."""
    return calculate_spot_price(
        state.shareReserves,
        state.bondReserves,
        state.lpTotalSupply,
        maturity_timestamp,
        block_timestamp,
        pool_config.positionDuration.iloc[0],
        pool_config.timeStretch.iloc[0],
        pool_config.initialSharePrice.iloc[0]
    )


def calculate_spot_price(
    share_reserves,
    bond_reserves,
    lp_total_supply,
    maturity_timestamp=None,
    block_timestamp=None,
    position_duration=None,
    time_stretch=None,
    initial_share_price=None
):
    """Calculate the spot price given the pool info data."""
    # pylint: disable=too-many-arguments

    # Hard coding variables to calculate spot price
    if initial_share_price is None:
        initial_share_price = 1
    if time_stretch is None:
        time_stretch = 0.045071688063194093
    full_term_spot_price = (
        (initial_share_price * share_reserves) / (bond_reserves + lp_total_supply)
    ) ** time_stretch

    if maturity_timestamp is None or block_timestamp is None or position_duration is None:
        return full_term_spot_price
    time_left_seconds = maturity_timestamp - block_timestamp
    if isinstance(time_left_seconds, pd.Timedelta):
        time_left_seconds = time_left_seconds.total_seconds()
    time_left_in_years = time_left_seconds / position_duration
    logging.info(
        " spot price is weighted average of %s(%s) and 1 (%s)",
        full_term_spot_price,
        time_left_in_years,
        1 - time_left_in_years,
    )

    return full_term_spot_price * time_left_in_years + 1 * (1 - time_left_in_years)


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
