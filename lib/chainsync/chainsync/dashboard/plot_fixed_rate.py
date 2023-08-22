"""Plot the fixed rate."""
from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib import ticker as mpl_ticker


def plot_fixed_rate(data, axes):
    """Returns the fixed rate plot"""
    axes.plot(data["timestamp"], data["fixed_rate"])
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
