"""Builds the fixed rate dataframe to be plotted"""

import pandas as pd


def build_outstanding_positions(pool_info: pd.DataFrame) -> pd.DataFrame:
    """Gets the proper columns from pool analysis for plotting fixed rate

    Arguments
    ---------
    pool_info: pd.DataFrame
        The pool info object from `get_pool_info`

    Returns
    -------
    pd.DataFrame
        The ready to plot fixed rate
    """
    outstanding_positions = pool_info[["timestamp", "longs_outstanding", "shorts_outstanding"]]
    return outstanding_positions
