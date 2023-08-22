"""Plot the fixed rate."""
from __future__ import annotations

import matplotlib.pyplot as plt
from matplotlib import ticker as mpl_ticker


def plot_outstanding_positions(data, axes):
    """Returns the fixed rate plot"""
    axes.plot(data["timestamp"], data["longsOutstanding"], label="longs")
    axes.plot(data["timestamp"], data["shortsOutstanding"], label="shorts")
    # change y-axis unit format to 0.1%
    axes.yaxis.set_label_position("right")
    axes.yaxis.tick_right()
    axes.set_xlabel("block timestamp")
    axes.set_ylabel("bonds")
    axes.set_title("Open Positions")
    axes.legend()
    return plt.gcf()
