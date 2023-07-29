"""Plots the pnl."""
from __future__ import annotations

import logging

import pandas as pd
from extract_data_logs import calculate_spot_price


def calc_total_returns(pool_config: pd.Series, pool_info: pd.DataFrame, current_wallet: pd.DataFrame) -> pd.Series:
    """Calculates the most current pnl values."""
    # pylint: disable=too-many-locals
    # Most current block timestamp
    latest_pool_info = pool_info.loc[pool_info.index.max()]
    block_timestamp = latest_pool_info["timestamp"].timestamp()
    # Calculate for base
    base_balance = current_wallet[current_wallet["baseTokenType"] == "BASE"]["tokenValue"]
    # Calculate for lp
    wallet_lps = current_wallet[current_wallet["baseTokenType"] == "LP"]
    lp_returns = wallet_lps["tokenValue"] * latest_pool_info["sharePrice"]
    # Calculate for shorts
    wallet_shorts = current_wallet[current_wallet["baseTokenType"] == "SHORT"]
    short_spot_prices = calc_full_term_spot_price(
        latest_pool_info["shareReserves"],
        latest_pool_info["bondReserves"],
        pool_config["invTimeStretch"],
        pool_config["initialSharePrice"],
        pool_config["positionDuration"],
        wallet_shorts["maturityTime"],
        block_timestamp,
    )
    shorts_returns = wallet_shorts["tokenValue"] * (1 - short_spot_prices)
    # Calculate for longs
    wallet_longs = current_wallet[current_wallet["baseTokenType"] == "LONG"]
    long_spot_prices = calc_full_term_spot_price(
        latest_pool_info["shareReserves"],
        latest_pool_info["bondReserves"],
        pool_config["invTimeStretch"],
        pool_config["initialSharePrice"],
        pool_config["positionDuration"],
        wallet_longs["maturityTime"],
        block_timestamp,
    )
    long_returns = wallet_longs["tokenValue"] * long_spot_prices
    # Calculate for withdrawal shares
    wallet_withdrawl = current_wallet[current_wallet["baseTokenType"] == "WITHDRAWL_SHARE"]
    withdrawl_returns = wallet_withdrawl["tokenValue"] * latest_pool_info.sharePrice
    # Add pnl to current_wallet information
    # Index should match, so it's magic
    current_wallet.loc[base_balance.index, "pnl"] = base_balance
    current_wallet.loc[lp_returns.index, "pnl"] = lp_returns
    current_wallet.loc[shorts_returns.index, "pnl"] = shorts_returns
    current_wallet.loc[long_returns.index, "pnl"] = long_returns
    current_wallet.loc[withdrawl_returns.index, "pnl"] = withdrawl_returns
    total_returns = current_wallet.reset_index().groupby("walletAddress")["pnl"].sum()
    return total_returns


def calc_full_term_spot_price(
    share_reserves,
    bond_reserves,
    time_stretch,
    initial_share_price,
    position_duration,
    maturity_timestamp,
    block_timestamp,
):
    """Calculate the spot price given the pool info data."""
    full_term_spot_price = calculate_spot_price(share_reserves, bond_reserves, initial_share_price, time_stretch)
    time_left_seconds = maturity_timestamp - block_timestamp
    if isinstance(time_left_seconds, pd.Timedelta):
        time_left_seconds = time_left_seconds.total_seconds()
    time_left_in_years = time_left_seconds / position_duration
    logging.info(
        " spot price is weighted average of %s(%s) and 1 (%s)",
        full_term_spot_price,
        time_left_in_years,
        1 - time_left_in_years,
    )
    return full_term_spot_price * time_left_in_years + 1 * (1 - time_left_in_years)
