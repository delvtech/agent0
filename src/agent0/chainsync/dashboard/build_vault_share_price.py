"""Builds the variable rate dataframe to be plotted."""

import pandas as pd


def build_vault_share_price(pool_info: pd.DataFrame) -> pd.DataFrame:
    """Gets the proper columns from pool info for plotting variable rate.

    Arguments
    ---------
    pool_info: pd.DataFrame
        The pool analysis object from `get_pool_info`

    Returns
    -------
    pd.DataFrame
        The ready to plot variable rate
    """
    vault_share_price = pool_info[["timestamp", "vault_share_price"]].copy()
    vault_share_price["vault_share_price"] = vault_share_price["vault_share_price"].astype(float)
    # Return here as float for plotting
    return vault_share_price
