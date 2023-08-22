"""simulation for the Hyperdrive market"""
from __future__ import annotations

import mplfinance as mpf
from matplotlib import ticker as mpl_ticker


def plot_ohlcv(ohlcv, ohlcv_ax):
    """Plots the ohlcv plot"""
    if len(ohlcv > 0):
        mpf.plot(ohlcv, type="candle", ax=ohlcv_ax)

        ohlcv_ax.yaxis.set_major_formatter(mpl_ticker.FuncFormatter(lambda x, p: format(x, "0.6")))
        ohlcv_ax.set_xlabel("block timestamp")
        ohlcv_ax.set_title("OHLCV")
        ohlcv_ax.yaxis.set_label_position("right")
        ohlcv_ax.yaxis.tick_right()

    # format x-axis as time
