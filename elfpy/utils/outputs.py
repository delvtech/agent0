"""Helper functions for delivering simulation outputs"""
from __future__ import annotations

import json
import os
import sys
from logging.handlers import RotatingFileHandler
from typing import TYPE_CHECKING, Any

import matplotlib.pyplot as plt
import numpy as np
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from matplotlib import gridspec
from numpy.random._generator import Generator as NumpyGenerator
from web3.datastructures import AttributeDict, MutableAttributeDict

import elfpy

if TYPE_CHECKING:
    import pandas as pd
    from matplotlib.figure import Figure
    from matplotlib.gridspec import GridSpec
    from matplotlib.pyplot import Axes

# pylint: disable=too-many-locals
# pyright: reportGeneralTypeIssues=false


## Plotting
def plot_market_lp_reserves(
    state_df: pd.DataFrame, exclude_first_day: bool = True, exclude_last_day: bool = True
) -> Figure:
    r"""Plot the simulator market LP reserves per day

    Arguments
    ----------
    simulator : Simulator
        An instantiated simulator that has run trades with agents
    exclude_first_trade : bool
        If true, excludes the first day from the plot
    exclude_last_trade : bool
        If true, excludes the last day from the plot

    Returns
    -------
    Figure
    """
    fig, axes, _ = get_gridspec_subplots()
    start_idx = 1 if exclude_first_day else 0
    first_trade_that_is_on_last_day = min(state_df.index[state_df.day == max(state_df.day)])
    end_idx = first_trade_that_is_on_last_day - 1 if exclude_last_day is True else len(state_df)
    axis = state_df.iloc[start_idx:end_idx].plot(x="day", y="lp_reserves", ax=axes[0])
    axis.get_legend().remove()  # type: ignore
    axis.set_title("Market liquidity provider reserves")
    axis.set_ylabel("LP reserves")
    axis.set_xlabel("Day")
    return fig


def plot_market_spot_price(
    state_df: pd.DataFrame, exclude_first_day: bool = True, exclude_last_day: bool = True
) -> Figure:
    r"""Plot the simulator market APR per day

    Arguments
    ----------
    state_df : DataFrame
        Pandas dataframe containing the simulation_state keys as columns, as well as some computed columns
    exclude_first_trade : bool
        If true, excludes the first day from the plot
    exclude_last_trade : bool
        If true, excludes the last day from the plot

    Returns
    -------
    Figure
    """
    fig, axes, _ = get_gridspec_subplots()
    start_idx = 1 if exclude_first_day else 0
    first_trade_that_is_on_last_day = min(state_df.index[state_df.day == max(state_df.day)])
    end_idx = first_trade_that_is_on_last_day - 1 if exclude_last_day is True else len(state_df)
    axis = state_df.iloc[start_idx:end_idx].plot(x="day", y="spot_price", ax=axes[0])
    axis.get_legend().remove()  # type: ignore
    axis.set_title("Market spot price")
    axis.set_ylabel("Spot price of principle tokens")
    axis.set_xlabel("Day")
    return fig


def plot_agent_pnl(state_df: pd.DataFrame, exclude_first_agent: bool = True, exclude_first_day=True) -> Figure:
    r"""Plot the agent pnl

    Arguments
    ----------
    simulator : Simulator
        An instantiated simulator that has run trades with agents
    exclude_first_agent : bool
        If true, excludes the first agent from the plot
    exclude_first_day : bool
        If true, excludes the first day from the plot

    Returns
    -------
    Figure
    """
    num_agents = len([col for col in state_df if str(col).startswith("agent") and str(col).endswith("pnl")])
    agent_start_idx = 1 if exclude_first_agent else 0
    first_trade_that_is_on_second_day = min(state_df.index[state_df.day == min(state_df.day) + 1])
    day_start_idx = first_trade_that_is_on_second_day if exclude_first_day is True else 0
    fig, axes, _ = get_gridspec_subplots()
    axis = axes[0]
    for agent_id in range(agent_start_idx, num_agents):
        axis = state_df.iloc[day_start_idx:].plot(x="day", y=f"agent_{agent_id}_pnl", ax=axis)
    axis.set_title("Agent PNL Over Time")
    axis.set_ylabel("PNL")
    axis.set_xlabel("Day")
    return fig


def plot_lp_pnl(trades_agg: pd.DataFrame, exclude_last_day=True) -> Figure:
    r"""Plot the lp pnl

    Arguments
    ----------
    trades_agg : DataFrame
        Pandas dataframe containing the aggregated simulation_state keys as columns, as well as some computed columns
    exclude_last_day : bool
        If true, excludes the last day from the plot

    Returns
    -------
    Figure
    """
    num_agents = 1
    start_idx = 0
    first_trade_that_is_on_last_day = min(trades_agg.index[trades_agg.day == max(trades_agg.day)])
    end_idx = first_trade_that_is_on_last_day - 1 if exclude_last_day is True else len(trades_agg)
    fig, axes, _ = get_gridspec_subplots()
    axis = axes[0]
    for agent_id in range(start_idx, num_agents):
        axis = trades_agg.iloc[start_idx:end_idx].plot(x="day", y=f"agent_{agent_id}_pnl_mean", ax=axis)
    axis.set_title("LP PNL Over Time")
    axis.set_ylabel("PNL")
    axis.set_xlabel("Day")
    return fig


def plot_fixed_apr(state_df: pd.DataFrame, exclude_first_day: bool = True, exclude_last_day: bool = True) -> Figure:
    r"""Plot the simulator market APR per day

    Arguments
    ----------
    state_df : DataFrame
        Pandas dataframe containing the simulation_state keys as columns, as well as some computed columns
    exclude_first_trade : bool
        If true, excludes the first day from the plot
    exclude_last_trade : bool
        If true, excludes the last day from the plot

    Returns
    -------
    Figure
    """
    fig, axes, _ = get_gridspec_subplots()
    start_idx = 1 if exclude_first_day else 0
    first_trade_that_is_on_last_day = min(state_df.index[state_df.day == max(state_df.day)])
    end_idx = first_trade_that_is_on_last_day - 1 if exclude_last_day is True else len(state_df)
    axis = state_df.iloc[start_idx:end_idx].plot(x="day", y="fixed_apr_percent", ax=axes[0])
    axis.get_legend().remove()  # type: ignore
    axis.set_title("Market fixed APR")
    axis.set_ylabel("APR (%)")
    axis.set_xlabel("Day")
    return fig


def plot_fixed_volume(
    trades_agg: pd.DataFrame, exclude_first_trade: bool = True, exclude_last_trade: bool = True
) -> Figure:
    r"""Plot the simulator market APR per day

    Arguments
    ----------
    trades_agg : DataFrame
        Pandas dataframe containing the aggregated simulation_state keys as columns, as well as some computed columns
    exclude_first_trade : bool
        If true, excludes the first day from the plot (default = True)
    exclude_last_trade : bool
        If true, excludes the last day from the plot (default = True)

    Returns
    -------
    Figure
    """
    fig, axes, _ = get_gridspec_subplots()
    start_idx = 1 if exclude_first_trade else 0
    end_idx = -1 if exclude_last_trade is True else None
    axis = trades_agg.iloc[start_idx:end_idx].plot(x="day", y="delta_base_abs_sum", ax=axes[0], kind="bar")
    axis.get_legend().remove()  # type: ignore
    axis.set_title("Market Volume")
    axis.set_ylabel("Base")
    axis.set_xlabel("Day")
    return fig


def plot_longs_and_shorts(
    state_df: pd.DataFrame,
    exclude_first_agent: bool = True,
    exclude_first_trade: bool = True,
    xtick_step: int = 10,
) -> Figure:
    r"""Plot the total market longs & shorts over time

    Arguments
    ----------
    state_df : DataFrame
        Pandas dataframe containing the simulation_state keys as columns, as well as some computed columns
    exclude_first_agent : bool
        If true, exclude the first agent in simulator.agents (this is usually the init_lp agent)
    exclude_first_trade : bool
        If true, excludes the first day from the plot

    Returns
    -------
    Figure
    """
    fig, axes, _ = get_gridspec_subplots(nrows=1, ncols=2, wspace=0.5)
    start_idx = 1 if exclude_first_trade else 0
    addresses = []
    for column in state_df.columns:
        splits = str(column).split("_")
        if splits[0] == "agent":
            addresses.append(int(splits[1]))
    agents = set(addresses)
    for address in agents:
        if (exclude_first_agent and address > 0) or (not exclude_first_agent):
            dict_key = f"agent_{address}"
            _ = state_df.iloc[start_idx:].plot(
                x="run_trade_number", y=f"{dict_key}_total_longs", label=f"0x{address}", ax=axes[0]
            )
            _ = state_df.iloc[start_idx:].plot(
                x="run_trade_number", y=f"{dict_key}_total_shorts", label=f"0x{address}", ax=axes[1]
            )
    axes[0].set_ylabel("Total long balances")
    axes[1].set_ylabel("Total short balances")
    axes[0].legend()
    trade_labels = state_df.loc[:, "run_trade_number"][::xtick_step][:start_idx:]
    for axis in axes:
        axis.set_xlabel("Trade number")
        axis.set_xticks(trade_labels)
        axis.set_xticklabels([str(x + 1) for x in trade_labels])
        axis.set_box_aspect(1)
    fig_size = fig.get_size_inches()  # [width (or cols), height (or rows)]
    fig.set_size_inches([2 * fig_size[0], fig_size[1]])  # type: ignore
    _ = fig.suptitle("Longs and shorts per agent", y=0.90)
    return fig


def plot_wallet_reserves(
    state_df: pd.DataFrame,
    exclude_first_agent: bool = True,
    exclude_first_trade: bool = True,
    xtick_step: int = 10,
) -> Figure:
    r"""Plot the wallet base asset and LP token quantities over time

    Arguments
    ----------
    state_df : DataFrame
        Pandas dataframe containing the simulation_state keys as columns, as well as some computed columns
    exclude_first_agent : bool
        If true, exclude the first agent in simulator.agents (this is usually the init_lp agent)
    exclude_first_trade : bool
        If true, excludes the first day from the plot

    Returns
    -------
    Figure
    """
    fig, axes, _ = get_gridspec_subplots(nrows=1, ncols=2, wspace=0.5)
    start_idx = 1 if exclude_first_trade else 0
    addresses = []
    for column in state_df.columns:
        splits = str(column).split("_")
        if splits[0] == "agent":
            addresses.append(int(splits[1]))
    agents = set(addresses)
    for address in agents:
        if (exclude_first_agent and address > 0) or (not exclude_first_agent):
            dict_key = f"agent_{address}"
            _ = state_df.iloc[start_idx:].plot(
                x="run_trade_number", y=f"{dict_key}_base", label=f"0x{address}", ax=axes[0]
            )
            _ = state_df.iloc[start_idx:].plot(
                x="run_trade_number", y=f"{dict_key}_lp_tokens", label=f"0x{address}", ax=axes[1]
            )
    axes[0].set_ylabel("Base asset in wallet")
    axes[1].set_ylabel("LP tokens in wallet")
    axes[0].legend()
    trade_labels = state_df.loc[:, "run_trade_number"][::xtick_step][start_idx:]
    for axis in axes:
        axis.set_xlabel("Trade number")
        axis.set_xticks(trade_labels[start_idx:])
        axis.set_xticklabels([str(x + 1) for x in trade_labels][start_idx:])
        axis.set_box_aspect(1)
    fig_size = fig.get_size_inches()  # [width (or cols), height (or rows)]
    fig.set_size_inches([2 * fig_size[0], fig_size[1]])  # type: ignore
    _ = fig.suptitle("Agent wallet reserves", y=0.90)
    return fig


def get_gridspec_subplots(nrows: int = 1, ncols: int = 1, **kwargs: Any) -> tuple[Figure, list[Axes], GridSpec]:
    r"""Setup a figure with axes that have reasonable spacing

    Arguments
    ----------
    nrows : int
       number of rows in the figure
    ncols : int
       number of columns in the figure
    kwargs : Any
        optional keyword arguments to be supplied to matplotlib.gridspec.GridSpec()

    Returns
    -------
    tuple[Figure, Axes, GridSpec]
        a tuple containing the relevant figure objects
    """
    if "wspace" not in kwargs:
        kwargs["wspace"] = 1.0
    grid_spec = gridspec.GridSpec(nrows, ncols, **kwargs)
    fig: Figure = plt.figure()
    axes: list[Axes] = [fig.add_subplot(grid_spec[plot_id]) for plot_id in np.ndindex(nrows, ncols)]
    return fig, axes, grid_spec


def clear_axis(axis: Axes, spines: str = "none") -> Axes:
    r"""Clear spines & tick labels from proplot axis object

    Arguments
    ----------
        axis : matplotlib axis object
           axis to be cleared
        spines : str
           any matplotlib color, defaults to "none" which makes the spines invisible

    Returns
    -------
        axis : matplotlib axis object
    """
    for ax_loc in ["top", "bottom", "left", "right"]:
        axis.spines[ax_loc].set_color(spines)
    axis.set_yticklabels([])
    axis.set_xticklabels([])
    axis.get_xaxis().set_visible(False)
    axis.get_yaxis().set_visible(False)
    axis.tick_params(axis="both", bottom=False, top=False, left=False, right=False)
    return axis


def clear_axes(axes: list[Axes], spines: str = "none") -> list:
    r"""Calls clear_axis iteratively for each axis in axes

    Arguments
    ----------
        axes : list of matplotlib axis objects
           axes to be cleared
        spines : str
           any matplotlib color, defaults to "none" which makes the spines invisible

    Returns
    -------
        axes : list of matplotlib axis objects
    """
    for axis in axes:
        clear_axis(axis, spines)
    return axes


def format_axis(
    axis_handle, xlabel="", fontsize=18, linestyle="--", linewidth="1", color="grey", which="both", axis="y"
):
    r"""Formats the axis"""
    # pylint: disable=too-many-arguments
    axis_handle.set_xlabel(xlabel)
    axis_handle.tick_params(axis="both", labelsize=fontsize)
    axis_handle.grid(visible=True, linestyle=linestyle, linewidth=linewidth, color=color, which=which, axis=axis)
    if xlabel == "":
        axis_handle.xaxis.set_ticklabels([])
    axis_handle.legend(fontsize=fontsize)


def annotate(axis_handle, text, major_offset, minor_offset, val):
    r"""Adds legend-like labels"""
    annotation_handle = axis_handle.annotate(
        text,
        xy=(
            val["position_x"],
            val["position_y"] - val["major_offset"] * major_offset - val["minor_offset"] * minor_offset,
        ),
        xytext=(
            val["position_x"],
            val["position_y"] - val["major_offset"] * major_offset - val["minor_offset"] * minor_offset,
        ),
        xycoords="subfigure fraction",
        fontsize=val["font_size"],
        alpha=val["alpha"],
    )
    annotation_handle.set_bbox(
        {"facecolor": "white", "edgecolor": "black", "alpha": val["alpha"], "linewidth": 0, "boxstyle": "round,pad=0.1"}
    )


class ExtendedJSONEncoder(json.JSONEncoder):
    r"""Custom encoder for JSON string dumps"""
    # pylint: disable=too-many-return-statements

    def default(self, o):
        r"""Override default behavior"""
        if isinstance(o, set):
            return list(o)
        if isinstance(o, HexBytes):
            return o.hex()
        if isinstance(o, (AttributeDict, MutableAttributeDict)):
            return dict(o)
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.ndarray):
            return o.tolist()
        if isinstance(o, FixedPoint):
            return str(o)
        if isinstance(o, NumpyGenerator):
            return "NumpyGenerator"
        try:
            return o.__dict__
        except AttributeError:
            pass
        # Let the base class default method raise the TypeError
        return json.JSONEncoder.default(self, o)
