"""Plot the fixed rate."""
from __future__ import annotations

import matplotlib.pyplot as plt
from ethpy.hyperdrive import BASE_TOKEN_SYMBOL


def plot_outstanding_positions(data, axes):
    """Returns the fixed rate plot"""
    bonds_symbol = "Hy" + BASE_TOKEN_SYMBOL

    axes.plot(data["timestamp"], data["longsOutstanding"], label="Longs")
    axes.plot(data["timestamp"], data["shortsOutstanding"], label="Shorts")
    # change y-axis unit format to 0.1%
    axes.yaxis.set_label_position("right")
    axes.yaxis.tick_right()
    axes.set_xlabel("Block Timestamp")
    axes.set_ylabel(bonds_symbol)
    axes.set_title("Open Positions")
    axes.legend()
    return plt.gcf()
