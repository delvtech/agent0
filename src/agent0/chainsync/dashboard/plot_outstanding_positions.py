"""Plot the fixed rate."""

from __future__ import annotations

import pandas as pd
from matplotlib.axes import Axes

from agent0.ethpy.hyperdrive import BASE_TOKEN_SYMBOL


def plot_outstanding_positions(data: pd.DataFrame, axes: Axes):
    """Returns the fixed rate plot.

    Arguments
    ---------
    data: pd.DataFrame
        The data to plot.
    axes: Axes
        The matplotlib axes to plot on.
    """
    bonds_symbol = "hy" + BASE_TOKEN_SYMBOL

    axes.plot(data["timestamp"], data["longs_outstanding"], label="Longs")
    axes.plot(data["timestamp"], data["shorts_outstanding"], label="Shorts")
    # change y-axis unit format to 0.1%
    axes.yaxis.set_label_position("right")
    axes.yaxis.tick_right()
    axes.set_xlabel("Block Timestamp")
    axes.set_ylabel(bonds_symbol)
    axes.set_title("Open Positions")
    axes.legend()
