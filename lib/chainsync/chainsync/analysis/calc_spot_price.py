"""Calculate the spot price."""

from decimal import ROUND_DOWN, Decimal, localcontext

import pandas as pd


# TODO these functions should be deprecated in favor of external call
# Keeping share_reserves and bond_reserves as pd.Series in case we want to batch process spot prices
def calc_spot_price(
    share_reserves: pd.Series,
    share_adjustment: pd.Series,
    bond_reserves: pd.Series,
    initial_share_price: Decimal,
    time_stretch: Decimal,
):
    """Calculate the spot price."""
    # Keep decimal places to 18 decimal places
    with localcontext() as ctx:
        ctx.prec = 18
        ctx.rounding = ROUND_DOWN
        effective_share_reserves = share_reserves - share_adjustment
        # Sanity check
        if isinstance(effective_share_reserves, pd.Series):
            assert (effective_share_reserves >= 0).all()
        else:
            assert effective_share_reserves >= 0  # When it's a scalar or other type
        # Pandas is smart enough to be able to broadcast with internal Decimal types at runtime
        spot_price = ((initial_share_price * effective_share_reserves) / bond_reserves) ** time_stretch  # type: ignore
    return spot_price
