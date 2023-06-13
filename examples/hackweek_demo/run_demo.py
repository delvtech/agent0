"""Do the analysis."""
# std lib
from pathlib import Path
import time
from collections import namedtuple
from matplotlib.figure import Figure

# third party
import pandas as pd
import mplfinance as mpf
import streamlit as st

# local
from plot_ohlcv import plot_ohlcv, calc_ohlcv
from plot_fixed_rate import calc_fixed_rate, plot_fixed_rate
from plot_pnl import calculate_pnl, plot_pnl

SAVE_FOLDER = Path(__file__).parent.parent.parent / ".logging"

# set up streamlit
st.set_page_config(
    page_title="Bots dashboard",
    layout="wide",
)
st.set_option("deprecation.showPyplotGlobalUse", False)
ticker_col, plot_col = st.columns([0.4, 0.6])
with ticker_col:
    st.title("🤖 The Robot Takeover")
    st.header("🚀 Get ready to blast off into Hyperdrive")
    lhs = st.empty()
with plot_col:
    rhs = st.empty()
footer = st.empty()  # creating a single-element streamlit container

# set up analysis
fig = mpf.figure(style="mike", figsize=(15, 15))
DataAxes = namedtuple("DataAxes", ["ohlcv", "fixed_rate", "volume", "pnl"])
ax = DataAxes(
    ohlcv=fig.add_subplot(2, 2, 1),
    fixed_rate=fig.add_subplot(2, 2, 2),
    volume=fig.add_subplot(2, 2, 3),
    pnl=fig.add_subplot(2, 2, 4),
)
assert isinstance(fig, Figure), f"{fig=} is not a Figure object"
fig.set_tight_layout(True)

conf_file = SAVE_FOLDER / "pool_config.csv"
config_df = pd.read_csv(conf_file) if conf_file.exists() else None
if config_df is None:
    footer.warning("Waiting for config...")
else:
    footer.success("Config loaded")

pool_file = SAVE_FOLDER / "pool.csv"
logs_file = SAVE_FOLDER / "logs.csv"
while True:  # main loop
    while True:  # read data loop
        try:
            pool_df = pd.read_csv(pool_file) if pool_file.exists() else None
            logs_df = pd.read_csv(logs_file) if logs_file.exists() else None
            break
        except pd.errors.EmptyDataError as exc:
            footer.warning("Could not read data")
            time.sleep(0.1)
    if pool_df is None or logs_df is None:
        footer.warning("Waiting for data...")
    else:
        # Calculate OHLCV and fixed rate (in poolinfo)
        ohlcv = calc_ohlcv(pool_df, freq="5T")
        fixed_rate_x, fixed_rate_y = calc_fixed_rate(pool_df)
        pnl_x, pnl_y = calculate_pnl(logs_df, config_df)
        logs_df["base"] = logs_df["baseAmount"].astype(float) / 1e18
        logs_df["bonds"] = logs_df["bondAmount"].astype(float) / 1e18
        logs_df["shareReserves"] = round(logs_df["shareReserves"].astype(float) / 1e18)
        logs_df["bondReserves"] = round(logs_df["bondReserves"].astype(float) / 1e18)
        logs_df["lpTotalSupply"] = round(logs_df["lpTotalSupply"].astype(float) / 1e18)
        # Plot reserve levels (share and bond reserves, in poolinfo)
        # Fix axes labels
        # Add ticker
        logs_df.rename(columns={"blockNumber": "block"}, inplace=True)
        cols = ["event", "block", "base", "bonds", "shareReserves", "bondReserves", "lpTotalSupply"]
        trades = logs_df.loc[logs_df.event != "TransferSingle", :]
        lhs.dataframe(trades.loc[:-100:-1, cols], height=850)
        for a in ax:  # clear all axes
            a.clear()
        plot_ohlcv(ohlcv, ax.ohlcv, ax.volume)
        plot_fixed_rate(fixed_rate_x, fixed_rate_y, ax.fixed_rate)
        plot_pnl(pnl_x, pnl_y, ax.pnl)
        fig.autofmt_xdate()
        rhs.pyplot(fig=fig)
    old_stats_pool = Path.stat(pool_file)
    old_stats_logs = Path.stat(logs_file)
    footer.warning(msg := "Waiting for data...")
    while True:  # wait for data file to change before reading it in again
        new_stats_pool = Path.stat(pool_file)
        if new_stats_pool.st_mtime != old_stats_pool.st_mtime:
            footer.empty()
            break
        new_stats_logs = Path.stat(logs_file)
        if new_stats_logs.st_mtime != old_stats_logs.st_mtime:
            footer.empty()
            break
        footer.warning(msg := msg + ".")
        time.sleep(0.1)
