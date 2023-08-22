"""simulation for the Hyperdrive market"""
from __future__ import annotations

import mplfinance as mpf


def plot_ohlcv(ohlcv, ohlcv_ax):
    """Plots the ohlcv plot"""
    if len(ohlcv > 0):
        mpf.plot(ohlcv, type="candle", ax=ohlcv_ax)

        ohlcv_ax.set_xlabel("block timestamp")
        ohlcv_ax.set_title("OHLCV")
        ohlcv_ax.yaxis.set_label_position("right")
        ohlcv_ax.yaxis.tick_right()

    # format x-axis as time
