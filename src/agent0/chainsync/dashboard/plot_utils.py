"""Plot utilities for dashboard"""

import pandas as pd


def reduce_plot_data(data: pd.DataFrame, x_column_name: str, y_column_name: str) -> pd.DataFrame:
    """Reduces the data we plot by looking for redundant rows with no change, and only return x and y columns

    Arguments
    ---------
    data: pd.DataFrame
        The data to plot.
    x_column_name: str
        The name of the x column
    y_column_name: str
        The name of the y column

    Returns
    -------
    pd.DataFrame
        The reduced data
    """

    plot_data = data[[x_column_name, y_column_name]]

    # Check for empty data frame
    if len(plot_data) == 0:
        return plot_data

    # Filter out rows with no change

    # We want both points before and after the change
    # so we look at the diffs in both directions, and plot it
    # if either one is not 0
    data_diff = plot_data[y_column_name].diff()
    reverse_data_diff = plot_data[y_column_name][::-1].diff()[::-1]

    # Filter out intermediate rows with no difference
    plot_data_idx = (data_diff != 0) | (reverse_data_diff != 0)
    return plot_data[plot_data_idx]
