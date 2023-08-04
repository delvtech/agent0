"""Plots the pnl."""
from __future__ import annotations

import logging

import pandas as pd

from elf_simulations.dashboard.extract_data_logs import calculate_spot_price


def calc_total_returns(pool_config: pd.Series, pool_info: pd.DataFrame, wallet_deltas: pd.DataFrame) -> pd.Series:
    """Calculate the most current pnl values.

    Calculate_spot_price_for_position calculates the spot price for a position that has matured by some amount.

    Arguments
    ---------
    pool_config : pd.Series
        Time-invariant pool configuration.
    pool_info : pd.DataFrame
        Pool information like reserves. This can contain multiple blocks, but only the most recent is used.
    wallet_deltas: pd.DataFrame
        Wallet deltas for each agent and position.

    Returns
    -------
    pd.Series
        Calculated pnl for each row in current_wallet.
    """
    # pylint: disable=too-many-locals
    # Most current block timestamp
    latest_pool_info = pool_info.loc[pool_info.index.max()]
    block_timestamp = latest_pool_info["timestamp"].timestamp()

    # Calculate unrealized gains
    current_wallet = wallet_deltas.groupby(["walletAddress", "tokenType"]).agg(
        {"delta": "sum", "baseTokenType": "first", "maturityTime": "first"}
    )

    # Sanity check, no tokens except base should dip below 0
    assert (current_wallet["delta"][current_wallet["baseTokenType"] != "BASE"] >= 0).all()

    # Calculate for base
    # Base is valued at 1:1, since that's our numéraire (https://en.wikipedia.org/wiki/Num%C3%A9raire)
    wallet_base = current_wallet[current_wallet["baseTokenType"] == "BASE"]
    base_returns = wallet_base["delta"]

    # Calculate for lp
    # LP value = users_LP_tokens * sharePrice
    # derived from:
    #   total_lp_value = lpTotalSupply * sharePrice
    #   share_of_pool = users_LP_tokens / lpTotalSupply
    #   users_LP_value = share_of_pool * total_lp_value
    #   users_LP_value = users_LP_tokens / lpTotalSupply * lpTotalSupply * sharePrice
    #   users_LP_value = users_LP_tokens * sharePrice
    wallet_lps = current_wallet[current_wallet["baseTokenType"] == "LP"]
    lp_returns = wallet_lps["delta"] * latest_pool_info["sharePrice"]

    # Calculate for withdrawal shares. Same as for LPs.
    wallet_withdrawal = current_wallet[current_wallet["baseTokenType"] == "WITHDRAWAL_SHARE"]
    withdrawal_returns = wallet_withdrawal["delta"] * latest_pool_info["sharePrice"]

    # Calculate for shorts
    # Short value = users_shorts * ( 1 - spot_price )
    # this could also be valued at 1 + ( p1 - p2 ) but we'd have to know their entry price (or entry base 🤔)
    # TODO shorts inflate the pnl calculation. When opening a short, the "amount spent" is
    # how much base is put up for collateral, but the amount of short shares are being calculated at some price
    # This really should be, how much base do I get back if I close this short right now
    wallet_shorts = current_wallet[current_wallet["baseTokenType"] == "SHORT"]

    # This calculation isn't quite right, this is not accounting for the trade spot price
    # Should take into account the spot price slipping during the actual trade
    # This will get fixed when we call preview smart contract transaction for pnl calculations
    short_spot_prices = calculate_spot_price_for_position(
        share_reserves=latest_pool_info["shareReserves"],
        bond_reserves=latest_pool_info["bondReserves"],
        time_stretch=pool_config["invTimeStretch"],
        initial_share_price=pool_config["initialSharePrice"],
        position_duration=pool_config["positionDuration"],
        maturity_timestamp=wallet_shorts["maturityTime"],
        block_timestamp=block_timestamp,
    )

    shorts_returns = wallet_shorts["delta"] * (1 - short_spot_prices)

    # Calculate for longs
    # Long value = users_longs * spot_price
    wallet_longs = current_wallet[current_wallet["baseTokenType"] == "LONG"]
    long_spot_prices = calculate_spot_price_for_position(
        share_reserves=latest_pool_info["shareReserves"],
        bond_reserves=latest_pool_info["bondReserves"],
        time_stretch=pool_config["invTimeStretch"],
        initial_share_price=pool_config["initialSharePrice"],
        position_duration=pool_config["positionDuration"],
        maturity_timestamp=wallet_longs["maturityTime"],
        block_timestamp=block_timestamp,
    )
    long_returns = wallet_longs["delta"] * long_spot_prices

    # Add pnl to current_wallet information
    # Current_wallet and *_pnl dataframes have the same index
    current_wallet.loc[base_returns.index, "pnl"] = base_returns
    current_wallet.loc[lp_returns.index, "pnl"] = lp_returns
    current_wallet.loc[shorts_returns.index, "pnl"] = shorts_returns
    current_wallet.loc[long_returns.index, "pnl"] = long_returns
    current_wallet.loc[withdrawal_returns.index, "pnl"] = withdrawal_returns
    return current_wallet.reset_index().groupby("walletAddress")["pnl"].sum()


def calculate_spot_price_for_position(
    share_reserves: pd.Series,
    bond_reserves: pd.Series,
    time_stretch: pd.Series,
    initial_share_price: pd.Series,
    position_duration: pd.Series,
    maturity_timestamp: pd.Series,
    block_timestamp: pd.Series,
):
    """Calculate the spot price given the pool info data.

    This is calculated in a vectorized way, with every input being a scalar except for maturity_timestamp.

    Arguments
    ---------
    share_reserves : pd.Series
        The share reserves
    bond_reserves : pd.Series
        The bond reserves
    time_stretch : pd.Series
        The time stretch
    initial_share_price : pd.Series
        The initial share price
    position_duration : pd.Series
        The position duration
    maturity_timestamp : pd.Series
        The maturity timestamp
    block_timestamp : pd.Series
        The block timestamp
    """
    # pylint: disable=too-many-arguments
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
