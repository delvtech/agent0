from __future__ import annotations
from extract_data_logs import read_json_to_pd, explode_transaction_data, get_combined_data

import matplotlib.pyplot as plt
import mplfinance as mpf
import streamlit as st
import pandas as pd
import time

from plot_ohlcv import plot_ohlcv, calc_ohlcv
from plot_fixed_rate import calc_fixed_rate, plot_fixed_rate


# creating a single-element container
placeholder = st.empty()

# %%
# near real-time / live feed simulation

while True:
    # Hard coding location for now
    # trans_data = "hyperTransRecs_updated.json"

    ## Get transactions from data
    trans_data = "../../.logging/transactions.json"
    config_data = "../../.logging/hyperdrive_config.json"
    pool_info_data = "../../.logging/hyperdrive_pool_info.json"

    trans_data = explode_transaction_data(read_json_to_pd(trans_data))
    config_data = read_json_to_pd(config_data)
    pool_info_data = read_json_to_pd(pool_info_data).T

    combined_data = get_combined_data(trans_data, pool_info_data)

    ohlcv = calc_ohlcv(pool_info_data, freq='5T')

    (fixed_rate_x, fixed_rate_y) = calc_fixed_rate(combined_data)


    with placeholder.container():
        # create three columns
        (fig_col_1, fig_col_2) = st.columns(2)
        plt.close('all')
        with fig_col_1:
            st.markdown("## OHLCV plot")
            fig = plot_ohlcv(ohlcv)
            st.write(fig[0])
        with fig_col_2:
            st.markdown("## Fixed rates")
            fig = plot_fixed_rate(fixed_rate_x, fixed_rate_y)
            st.write(fig)

    time.sleep(.1)

