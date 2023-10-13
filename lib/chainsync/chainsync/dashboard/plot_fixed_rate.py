"""Plot the fixed rate."""
from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib import ticker as mpl_ticker


def plot_rates(fixed_rate, variable_rate, axes):
    """Returns the fixed rate plot"""
    axes.plot(fixed_rate["timestamp"], fixed_rate["fixed_rate"], label="Fixed rate")
    axes.plot(variable_rate["timestamp"], variable_rate["variable_rate"], label="Variable rate")
    # change y-axis unit format to 0.1%
    axes.yaxis.set_major_formatter(mpl_ticker.FuncFormatter(lambda x, p: format(x, "0.3%")))
    axes.yaxis.set_label_position("right")
    axes.yaxis.tick_right()
    axes.set_xlabel("block timestamp")
    axes.set_ylabel("rate (%)")
    axes.set_title("Fixed/Variable rate")
    axes.legend()
    return plt.gcf()
