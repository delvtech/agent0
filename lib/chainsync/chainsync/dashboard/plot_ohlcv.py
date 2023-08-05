# ---
# jupyter:
#   jupytext:
#     text_representation:
#       extension: .py
#       format_name: light
#       format_version: '1.5'
#       jupytext_version: 1.14.5
#   kernelspec:
#     display_name: Python 3 (ipykernel)
#     language: python
#     name: python3
# ---

# %%
"""simulation for the Hyperdrive market"""
from __future__ import annotations

import mplfinance as mpf
from chainsync.analysis import calc_ohlcv

# %%
# Get data here


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
