"""simulation for the Hyperdrive market"""

from __future__ import annotations

import mplfinance as mpf
import pandas as pd
from matplotlib import ticker as mpl_ticker
from matplotlib.axes import Axes


def plot_ohlcv(ohlcv: pd.DataFrame, ohlcv_ax: Axes) -> None:
    """Plots the ohlcv plot.

    Arguments
    ---------
    ohlcv: pd.DataFrame
        The ohlcv dataframe to plot.
    ohlcv_ax: Axes
        The matplotlib axes to plot on.
    """
    if len(ohlcv > 0):
        mpf.plot(ohlcv, type="candle", ax=ohlcv_ax, show_nontrading=True)

        ohlcv_ax.yaxis.set_major_formatter(mpl_ticker.FuncFormatter(lambda x, p: format(x, "0.6")))
        ohlcv_ax.set_xlabel("block timestamp")
        ohlcv_ax.set_title("Spot Price Ohlc")
        ohlcv_ax.yaxis.set_label_position("right")
        ohlcv_ax.yaxis.tick_right()

    # format x-axis as time
