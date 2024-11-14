"""Plot the fixed rate."""

from __future__ import annotations

import pandas as pd
from matplotlib.axes import Axes


def plot_share_price(vault_share_price: pd.DataFrame, axes: Axes) -> None:
    """Plots the vault share price.

    Arguments
    ---------
    vault_share_price: pd.DataFrame
        The vault_share_price dataframe.
    axes: Axes
        The matplotlib axes to plot on.
    """
    # TODO add lp share price to this plot
    axes.plot(vault_share_price["timestamp"], vault_share_price["vault_share_price"], label="Vault Share Price")
    axes.yaxis.set_label_position("right")
    axes.yaxis.tick_right()
    axes.set_xlabel("Timestamp")
    axes.set_ylabel("Share Price")
    axes.set_title("Share Price")
    axes.legend()
