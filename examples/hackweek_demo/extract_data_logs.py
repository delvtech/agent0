from __future__ import annotations
import json
import pandas as pd
import time

def read_json_to_pd(json_file):
    # Race condition if background process is writing, keep trying until it passes
    while True:
        try:
            with open(json_file, 'r', encoding='utf8') as f:
                json_data = json.load(f)
            break
        except json.JSONDecodeError:
            time.sleep(.1)
            continue

    return pd.DataFrame(json_data)

def explode_transaction_data(data):
    return pd.concat([
        pd.json_normalize(data['transaction']),
        pd.json_normalize(data['receipt'])
        ], axis=1)

def calculate_spot_price(pool_info_data):
    # Hard coding variables to calculate spot price
    initial_share_price = 1
    time_remaining_stretched = 0.045071688063194093
    spot_price = ((initial_share_price * (pool_info_data['shareReserves']/1e18)) /
        ((pool_info_data['bondReserves']/1e18) + (pool_info_data['lpTotalSupply']/1e18))
                 ) ** time_remaining_stretched
    return spot_price
