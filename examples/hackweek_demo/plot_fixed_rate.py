"""simulation for the Hyperdrive market"""
from __future__ import annotations

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import ticker as mpl_ticker

def calc_fixed_rate(pool_df):
    """Calculate the fixed rate given trade data."""
    pool_df["rate"] = (1-pool_df["spot_price"])/pool_df["spot_price"]

    x_data = pd.to_datetime(pool_df.loc[:, "timestamp"], unit="s")
    col_names = ["rate"]
    y_data = pool_df.loc[:, col_names]
    return x_data, y_data

def plot_fixed_rate(x_data, y_data, axes):
    """Plot the fixed rate plot."""
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
