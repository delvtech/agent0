from decimal import Decimal

import pandas as pd


def calc_base_buffer(longs_outstanding: pd.Series, share_price: pd.Series, minimum_share_reserves: Decimal):
    # Pandas is smart enough to be able to broadcast with internal Decimal types at runtime
    return longs_outstanding / share_price + minimum_share_reserves  # type: ignore
