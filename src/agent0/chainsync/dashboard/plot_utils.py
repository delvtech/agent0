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
    plot_data_diff = plot_data[y_column_name].diff()

    # We always keep the first and last rows
    # Diff always puts the first row as nan,
    # we explicitly set the last row as nan
    if len(plot_data_diff) > 0:
        # pandas doesn't play nice with types
        plot_data_diff.iloc[-1] = float("nan")  # type: ignore

    # Filter out intermediate rows with no difference
    # Note that nans will always not equal 0
    plot_data_idx = plot_data_diff != 0
    return plot_data[plot_data_idx]
