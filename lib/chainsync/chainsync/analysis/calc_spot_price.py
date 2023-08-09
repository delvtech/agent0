"""Calculate the spot price."""

import logging
from decimal import Decimal

import pandas as pd


# TODO these functions should be deprecated in favor of external call
def calculate_spot_price(share_reserves, bond_reserves, initial_share_price, time_stretch):
    """Calculate the spot price."""
    return ((initial_share_price * share_reserves) / bond_reserves) ** time_stretch


def calculate_spot_price_for_position(
    share_reserves: pd.Series,
    bond_reserves: pd.Series,
    time_stretch: pd.Series,
    initial_share_price: pd.Series,
    position_duration: pd.Series,
    maturity_timestamp: pd.Series,
    block_timestamp: Decimal,
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
    block_timestamp : Decimal
        The block timestamp
    """
    # pylint: disable=too-many-arguments
    full_term_spot_price = calculate_spot_price(share_reserves, bond_reserves, initial_share_price, time_stretch)
    time_left_seconds = maturity_timestamp - block_timestamp  # type: ignore
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
