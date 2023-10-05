"""Calculate the spot price."""

from decimal import Decimal

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
    # Pandas is smart enough to be able to broadcast with internal Decimal types at runtime
    effective_share_reserves = share_reserves - share_adjustment
    # Sanity check
    assert (effective_share_reserves >= 0).all()
    return ((initial_share_price * effective_share_reserves) / bond_reserves) ** time_stretch  # type: ignore
