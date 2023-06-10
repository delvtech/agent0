"""simulation for the Hyperdrive market"""
from __future__ import annotations
from extract_data_logs import read_json_to_pd, explode_transaction_data

import matplotlib.pyplot as plt
import mplfinance as mpf
import streamlit as st
import pandas as pd
import numpy as np
import time
from matplotlib import ticker as mpl_ticker
from matplotlib import dates as mdates

# %%
def calculate_spot_price_2(
        share_reserves, bond_reserves, lp_total_supply, maturity_timestamp, block_timestamp, position_duration
        ):
    """Calculate spot price."""
    # Hard coding variables to calculate spot price
    initial_share_price = 1
    time_remaining_stretched = 0.045071688063194093
    full_term_spot_price = (
            (initial_share_price * (share_reserves / 1e18)) / ((bond_reserves / 1e18) + (lp_total_supply / 1e18))
            ) ** time_remaining_stretched

    time_left_in_years = (maturity_timestamp - block_timestamp) / position_duration

    return full_term_spot_price * time_left_in_years + 1 * (1 - time_left_in_years)

def calc_fixed_rate(trade_data):
    # %%
    NUMBER_OF_DATA_ROWS_TO_PROCESS = len(trade_data)
    position_duration = max(trade_data["maturity_time"] - trade_data['block_timestamp'])
    position_duration_days = round(position_duration / 60 / 60 / 24)
    print(f"assuming position_duration is {position_duration_days}")
    position_duration = position_duration_days * 60 * 60 * 24

    # %%
    trade_data["rate"] = np.nan
    for idx, row in trade_data.iterrows():
        spot_price = calculate_spot_price_2(
                row.share_reserves,
                row.bond_reserves,
                row.lp_total_supply,
                row.block_timestamp + position_duration_days * 60 * 60 * 24, # term length in seconds
                row.block_timestamp,
                position_duration,
                )
        trade_data.loc[idx, "rate"] = ( 1 - spot_price ) / spot_price

    # %%
    x_data = pd.to_datetime(trade_data.loc[:,"block_timestamp"], unit="s")
    col_names = ["rate"]
    y_data = trade_data.loc[:,col_names]
    return (x_data, y_data)

def plot_fixed_rate(x_data, y_data):
    fig = plt.figure()
    plt.plot(x_data, y_data);
    # change y-axis unit format to 0.1%
    plt.gca().yaxis.set_major_formatter(mpl_ticker.FuncFormatter(lambda x, p: format(x, "0.3%")))
    plt.xlabel("block timestamp")
    plt.ylabel("rate (%)")
    plt.title("pnl over time")
    # format x-axis as time
    plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))

    #plt.gcf().autofmt_xdate()

    # make this work: col_names.replace("_pnl","")
    #plt.legend([col_names.replace("_pnl","") for col_names in col_names])

    return plt.gcf()
