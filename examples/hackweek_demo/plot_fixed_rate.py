"""simulation for the Hyperdrive market"""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from matplotlib import ticker as mpl_ticker

from extract_data_logs import calculate_spot_price

# %%


def calc_fixed_rate(trade_data):
    """
    Calculates the fixed rate given trade data
    """
    trade_data["rate"] = np.nan
    for idx, row in trade_data.iterrows():
        spot_price = calculate_spot_price(
            row.share_reserves,
            row.bond_reserves,
            row.lp_total_supply,
        )
        trade_data.loc[idx, "rate"] = (1 - spot_price) / spot_price

    x_data = pd.to_datetime(trade_data.loc[:, "block_timestamp"], unit="s")
    col_names = ["rate"]
    y_data = trade_data.loc[:, col_names]
    return (x_data, y_data)


def plot_fixed_rate(x_data, y_data, axes):
    """Plots the fixed rate plot"""
    axes.plot(x_data, y_data)
    # change y-axis unit format to 0.1%
    axes.yaxis.set_major_formatter(mpl_ticker.FuncFormatter(lambda x, p: format(x, "0.3%")))
    axes.yaxis.set_label_position("right")
    axes.yaxis.tick_right()
    axes.set_xlabel("block timestamp")
    axes.set_ylabel("rate (%)")
    axes.set_title("Fixed rate")

    # make this work: col_names.replace("_pnl","")
    # plt.legend([col_names.replace("_pnl","") for col_names in col_names])

    return plt.gcf()
