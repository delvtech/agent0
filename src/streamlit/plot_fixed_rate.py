"""simulation for the Hyperdrive market"""
from __future__ import annotations

import matplotlib.pyplot as plt
import numpy as np
from matplotlib import ticker as mpl_ticker

from eth_bots.streamlit.extract_data_logs import calculate_spot_price

# %%


def calc_fixed_rate(trade_data, config_data):
    """
    Calculates the fixed rate given trade data
    """
    trade_data["rate"] = np.nan
    annualized_time = config_data["positionDuration"] / (60 * 60 * 24 * 365)

    spot_price = calculate_spot_price(
        trade_data["share_reserves"],
        trade_data["bond_reserves"],
        config_data["initialSharePrice"],
        config_data["invTimeStretch"],
    )

    fixed_rate = (1 - spot_price) / (spot_price * annualized_time)

    x_data = trade_data["timestamp"]
    y_data = fixed_rate
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
