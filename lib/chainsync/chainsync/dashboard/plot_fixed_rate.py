"""Plot the fixed rate."""

from __future__ import annotations

import pandas as pd
from matplotlib import ticker as mpl_ticker
from matplotlib.axes import Axes


def plot_rates(fixed_rate: pd.DataFrame, variable_rate: pd.DataFrame, axes: Axes) -> None:
    """Plots the fixed and variable rates.

    Arguments
    ---------
    fixed_rate: pd.DataFrame
        The fixed rate dataframe.
    variable_rate: pd.DataFrame
        The variable rate dataframe.
    axes: Axes
        The matplotlib axes to plot on.
    """
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
