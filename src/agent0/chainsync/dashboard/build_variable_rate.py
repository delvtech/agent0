"""Builds the variable rate dataframe to be plotted."""

import pandas as pd


def build_variable_rate(pool_info: pd.DataFrame) -> pd.DataFrame:
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
    variable_rate = pool_info[["timestamp", "variable_rate"]].copy()
    variable_rate["variable_rate"] = variable_rate["variable_rate"].astype(float)
    variable_rate = variable_rate.rename(columns={"variable_rate": "variable_rate"})
    # Return here as float for plotting
    return variable_rate
