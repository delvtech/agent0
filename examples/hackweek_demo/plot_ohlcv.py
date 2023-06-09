# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
"""simulation for the Hyperdrive market"""
from __future__ import annotations
import json
import pandas as pd

import mplfinance as mpf

import streamlit as st

# %%
# Get data here
st.set_page_config(
    page_title="Bots dashboard",
    layout="wide",
    )
st.set_option('deprecation.showPyplotGlobalUse', False)

# %%
# Hard coding location for now
trans_data = "hyperTransRecs_updated.json"

with open(trans_data, 'r', encoding='utf8') as f:
    json_data = json.load(f)

data = pd.DataFrame(json_data)

def get_decoded_logs(data):
    timestamps = data['timestamp']
    decoded_logs = data['decoded_logs'].reset_index().explode('decoded_logs')
    index = decoded_logs['index']
    decoded_logs = pd.json_normalize(decoded_logs['decoded_logs'])
    decoded_logs['timestamp'] = pd.to_datetime(timestamps.loc[index].values, unit='s')
    # Filter for only transfers
    decoded_logs['data_index'] = index.values
    decoded_logs = decoded_logs[decoded_logs['event'] == "TransferSingle"]
    return decoded_logs

def get_decoded_input(data):
    timestamps = data['timestamp']
    decoded_input = pd.json_normalize(data['decoded_input'])
    decoded_input['timestamp'] = pd.to_datetime(timestamps, unit='s')
    return decoded_input



def calculate_spot_price(decoded_logs):
    # Hard coding variables to calculate spot price
    initial_share_price = 1
    time_remaining_stretched = 0.045071688063194093
    spot_price = ((initial_share_price * (decoded_logs['block_info.shareReserves_']/1e18)) /
        ((decoded_logs['block_info.bondReserves_']/1e18) + (decoded_logs['block_info.lpTotalSupply']/1e18))
                 ) ** time_remaining_stretched
    return spot_price


def calc_ohlcv(data, freq='D'):
    decoded_logs = get_decoded_logs(data)
    decoded_logs['spot_price'] = calculate_spot_price(decoded_logs)
    decoded_logs['value'] = decoded_logs['args.value']/1e18
    decoded_logs = decoded_logs.set_index('timestamp')

    ohlcv = decoded_logs.groupby([
        pd.Grouper(freq=freq)
    ]).agg({'spot_price':['first', 'last', 'max', 'min'], 'value':'sum'})

    ohlcv.columns = ['Open', 'Close', 'High', 'Low', 'Volume']
    ohlcv.index.name = 'Date'

    return ohlcv.astype(float)



ohlcv = calc_ohlcv(data)

mpf.plot(ohlcv, style='mike', type='candle', volume=True)

# %%

# Show plot in streamlit
st.pyplot()


