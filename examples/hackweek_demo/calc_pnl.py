"""Plots the pnl."""
from __future__ import annotations

import logging

import pandas as pd
from extract_data_logs import calculate_spot_price


# TODO fix calculating spot price with position duration
def calculate_spot_price_from_state(state, maturity_timestamp, block_timestamp, config_data):
    """Calculate spot price from reserves stored in a state variable."""
    return calculate_spot_price_for_position(
        state.shareReserves,
        state.bondReserves,
        config_data["invTimeStretch"],
        config_data["initialSharePrice"],
        config_data["positionDuration"],
        maturity_timestamp,
        block_timestamp,
    )


# Old calculate spot price
def calculate_spot_price_for_position(
    share_reserves,
    bond_reserves,
    time_stretch,
    initial_share_price,
    position_duration,
    maturity_timestamp,
    block_timestamp,
):
    """Calculate the spot price given the pool info data."""
    # pylint: disable=too-many-arguments

    # TODO this calculation is broken
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


def calculate_current_pnl(pool_config: pd.Series, pool_info: pd.DataFrame, current_wallet: pd.DataFrame) -> pd.Series:
    """Calculates the most current pnl values."""
    # Most current block timestamp
    latest_pool_info = pool_info.loc[pool_info.index.max()]
    block_timestamp = latest_pool_info["timestamp"].timestamp()

    # Calculate for base
    base_pnl = current_wallet[current_wallet["baseTokenType"] == "BASE"]["tokenValue"]

    # Calculate for lp
    wallet_lps = current_wallet[current_wallet["baseTokenType"] == "LP"]
    lp_pnl = wallet_lps["tokenValue"] * latest_pool_info["sharePrice"]

    # Calculate for shorts
    wallet_shorts = current_wallet[current_wallet["baseTokenType"] == "SHORT"]
    short_spot_prices = calculate_spot_price_for_position(
        latest_pool_info["shareReserves"],
        latest_pool_info["bondReserves"],
        pool_config["invTimeStretch"],
        pool_config["initialSharePrice"],
        pool_config["positionDuration"],
        wallet_shorts["maturityTime"],
        block_timestamp,
    )
    shorts_pnl = wallet_shorts["tokenValue"] * (1 - short_spot_prices)

    # Calculate for longs
    wallet_longs = current_wallet[current_wallet["baseTokenType"] == "LONG"]
    long_spot_prices = calculate_spot_price_for_position(
        latest_pool_info["shareReserves"],
        latest_pool_info["bondReserves"],
        pool_config["invTimeStretch"],
        pool_config["initialSharePrice"],
        pool_config["positionDuration"],
        wallet_longs["maturityTime"],
        block_timestamp,
    )
    long_pnl = wallet_longs["tokenValue"] * long_spot_prices

    # Add pnl to current_wallet information
    # Index should match, so it's magic
    current_wallet.loc[base_pnl.index, "pnl"] = base_pnl
    current_wallet.loc[lp_pnl.index, "pnl"] = lp_pnl
    current_wallet.loc[shorts_pnl.index, "pnl"] = shorts_pnl
    current_wallet.loc[long_pnl.index, "pnl"] = long_pnl
    pnl = current_wallet.reset_index().groupby("walletAddress")["pnl"].sum()
    return pnl
