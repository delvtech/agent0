"""simulation for the Hyperdrive market"""
from __future__ import annotations

import mplfinance as mpf
import pandas as pd
from chainsync.analysis.calc_spot_price import calc_spot_price


def plot_ohlcv(ohlcv, ohlcv_ax, vol_ax):
    """Plots the ohlcv plot"""
    if len(ohlcv > 0):
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


def calc_ohlcv(trade_data, config_data, freq="D"):
    """
    freq var: https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#offset-aliases
    """
    spot_prices = (
        calc_spot_price(
            trade_data["share_reserves"],
            trade_data["bond_reserves"],
            config_data["initialSharePrice"],
            config_data["invTimeStretch"],
        )
        .to_frame()
        .astype(float)
    )

    spot_prices.columns = ["spot_price"]
    value = trade_data["value"]

    spot_prices["value"] = value
    spot_prices["timestamp"] = trade_data["timestamp"]
    spot_prices = spot_prices.set_index("timestamp")

    ohlcv = spot_prices.groupby([pd.Grouper(freq=freq)]).agg(
        {"spot_price": ["first", "last", "max", "min"], "value": "sum"}
    )

    ohlcv.columns = ["Open", "Close", "High", "Low", "Volume"]
    ohlcv.index.name = "Date"

    return ohlcv

    # format x-axis as time
