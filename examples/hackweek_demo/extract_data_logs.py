from __future__ import annotations
import json
import pandas as pd
import time


def read_json_to_pd(json_file):
    # Race condition if background process is writing, keep trying until it passes
    while True:
        try:
            with open(json_file, "r", encoding="utf8") as f:
                json_data = json.load(f)
            break
        except json.JSONDecodeError:
            time.sleep(0.1)
            continue

    return pd.DataFrame(json_data)


def explode_transaction_data(data):
    cat_data = pd.concat([pd.json_normalize(data["transaction"]), pd.json_normalize(data["receipt"])], axis=1)
    cat_data = cat_data.loc[:, ~cat_data.columns.duplicated()].copy()
    return cat_data


def calculate_spot_price(pool_info_data):
    # Hard coding variables to calculate spot price
    initial_share_price = 1
    time_remaining_stretched = 0.045071688063194093
    spot_price = (
        (initial_share_price * (pool_info_data["shareReserves"] / 1e18))
        / ((pool_info_data["bondReserves"] / 1e18) + (pool_info_data["lpTotalSupply"] / 1e18))
    ) ** time_remaining_stretched
    return spot_price


def get_combined_data(trans_data, pool_info_data):
    pool_info_data.index = pool_info_data.index.astype(int)
    trans_data.index = trans_data["blockNumber"]
    # Combine pool info data and trans data by block number
    data = trans_data.merge(pool_info_data, left_index=True, right_index=True)
    data["timestamp"] = data["timestamp"].astype(int)

    rename_dict = {
        "contractAddress": "contract_address",
        "transactionHash": "transaction_hash",
        "blockNumber": "block_number",
        "blockHash": "block_hash",
        "transactionIndex": "transaction_index",
        "args.operator": "operator",  # missing
        "args.from": "from",  # missing
        "args.to": "to",  # missing
        "args.id": "id",  # missing
        "args.value": "value",  # missing
        "prefix": "prefix",  # missing
        "input.params._maturityTime": "maturity_timestamp",
        "input.method": "trade_type",
        "shareReserves": "share_reserves",
        "bondReserves": "bond_reserves",
        "lpTotalSupply": "lp_total_supply",
        "sharePrice": "share_price",
        "longsOutstanding": "longs_outstanding",
        "longAverageMaturityTime": "longs_average_maturity_time",
        "shortsOutstanding": "shorts_outstanding",
        "shortAverageMaturityTime": "short_average_maturity_time",
        "shortBaseVolume": "short_base_volume",
        "input.params._maturityTime": "maturity_time",
        "timestamp": "block_timestamp",
    }

    # %%
    columns = [k for k in rename_dict.keys()]

    # TODO remove this hack, only grab columns that exist from data
    columns = [c for c in columns if c in data.columns]

    # %%
    # Filter data based on columns
    trade_data = data[columns]
    # Rename columns
    trade_data = trade_data.rename(columns=rename_dict)
    return trade_data
