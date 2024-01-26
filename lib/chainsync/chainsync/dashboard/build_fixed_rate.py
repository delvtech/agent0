"""Builds the fixed rate dataframe to be plotted"""

import pandas as pd


def build_fixed_rate(pool_analysis: pd.DataFrame) -> pd.DataFrame:
    """Gets the proper columns from pool analysis for plotting fixed rate

    Arguments
    ---------
    pool_analysis: pd.DataFrame
        The pool analysis object from `get_pool_anlysis`

    Returns
    -------
    pd.DataFrame
        The ready to plot fixed rate
    """
    fixed_rate = pool_analysis[["timestamp", "fixed_rate"]].copy()
    fixed_rate["fixed_rate"] = fixed_rate["fixed_rate"].astype(float)
    # Return here as float for plotting
    return fixed_rate
