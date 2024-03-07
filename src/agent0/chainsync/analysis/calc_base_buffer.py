"""Calculates the amount of base set aside that can't be withdrawn"""

from decimal import Decimal

import pandas as pd


def calc_base_buffer(
    longs_outstanding: pd.Series, vault_share_price: pd.Series, minimum_share_reserves: Decimal
) -> pd.Series:
    """Calculates the amount of base set aside that can't be withdrawn

    Arguments
    ---------
    longs_outstanding: pd.Series
        The number of longs outstanding from the pool info
    vault_share_price: pd.Series
        The vault share price from the pool info
    minimum_share_reserves: Decimal
        The minimum share reserves from the pool config

    Returns
    -------
    pd.Series
        The base buffer.
    """
    # Pandas is smart enough to be able to broadcast with internal Decimal types at runtime
    return longs_outstanding / vault_share_price + minimum_share_reserves  # type: ignore
