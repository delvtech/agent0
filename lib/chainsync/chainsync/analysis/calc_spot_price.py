"""Calculate the spot price."""

from decimal import ROUND_DOWN, Decimal, localcontext

import pandas as pd


# TODO these functions should be deprecated in favor of external call
# Keeping share_reserves and bond_reserves as pd.Series in case we want to batch process spot prices
def calc_spot_price(
    share_reserves: pd.Series,
    share_adjustment: pd.Series,
    bond_reserves: pd.Series,
    initial_vault_share_price: Decimal,
    time_stretch: Decimal,
) -> pd.Series:
    """Calculate the spot price.

    Arguments
    ---------
    share_reserves: pd.Series
        The share reserves from the pool info.
    share_adjustment: pd.Series
        The share adjustment from the pool info.
    bond_reserves: pd.Series
        The bond reserves from the pool info.
    initial_vault_share_price: Decimal
        The initial vault share price from the pool config.
    time_stretch: Decimal
        The time stretch from the pool config.

    Returns
    -------
    pd.Series
        The spot prices.
    """
    # Keep decimal places to 18 decimal places
    with localcontext() as ctx:
        ctx.prec = 18
        ctx.rounding = ROUND_DOWN
        effective_share_reserves = share_reserves - share_adjustment
        # Sanity check
        assert (effective_share_reserves >= 0).all()
        # Pandas is smart enough to be able to broadcast with internal Decimal types at runtime
        spot_price = (
            (initial_vault_share_price * effective_share_reserves) / bond_reserves  # type: ignore
        ) ** time_stretch
    return spot_price
