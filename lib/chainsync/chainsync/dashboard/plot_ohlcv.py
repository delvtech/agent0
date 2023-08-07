"""simulation for the Hyperdrive market"""
from __future__ import annotations

import mplfinance as mpf


def plot_ohlcv(ohlcv, ohlcv_ax, vol_ax):
    """Plots the ohlcv plot"""
    mpf.plot(ohlcv, type="candle", volume=vol_ax, ax=ohlcv_ax)

    ohlcv_ax.set_xlabel("block timestamp")
    ohlcv_ax.set_title("OHLCV")
    ohlcv_ax.yaxis.set_label_position("right")
    ohlcv_ax.yaxis.tick_right()

    vol_ax.set_xlabel("block timestamp")
    vol_ax.set_ylabel("Volume")
    vol_ax.set_title("Volume")
    vol_ax.yaxis.set_label_position("right")
    vol_ax.yaxis.tick_right()

    # format x-axis as time
