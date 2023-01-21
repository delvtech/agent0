"""
Helper functions for post-processing simulation outputs
"""
from __future__ import annotations  # types will be strings by default in 3.11
from typing import TYPE_CHECKING
import os
import sys
import json
import logging
from logging.handlers import RotatingFileHandler

import numpy as np
import matplotlib.pyplot as plt
from matplotlib import gridspec

import elfpy

if TYPE_CHECKING:
    from typing import Optional, Any
    from matplotlib.figure import Figure
    from matplotlib.gridspec import GridSpec
    from matplotlib.pyplot import Axes
    from elfpy.simulators import Simulator


## Plotting
def plot_wallet_returns(simulator: Simulator, exclude_first_agent: bool = True) -> Figure:
    """
    Plot the wallet base asset and LP token quantities over time

    Arguments
    ---------
    simulator : Simulator
        An instantiated simulator that has run trades with agents

    exclude_first_agent : bool
        If true, exclude the first agent in simulator.agents (this is usually the init_lp agent)

    Returns
    ---------
    Figure
    """
    xtick_step = 10
    nrows = 1
    ncols = 2
    fig, axes, _ = get_gridspec_subplots(nrows, ncols, wspace=0.5)
    for address in simulator.agents:
        if exclude_first_agent and address > 0:
            dict_key = f"agent_{address}"
            axes[0].plot(
                [item[2] for item in simulator.simulation_state[dict_key] if item is not None], label=f"agent {address}"
            )
            axes[1].plot(
                [item[3] for item in simulator.simulation_state[dict_key] if item is not None], label=f"agent {address}"
            )
    axes[0].set_ylabel("Base asset in wallet")
    axes[1].set_ylabel("LP tokens in wallet")
    axes[0].legend()
    trade_labels = simulator.simulation_state.run_trade_number[::xtick_step]
    for axis in axes:
        axis.set_xlabel("Trade number")
        axis.set_xticks(trade_labels)
        axis.set_xticklabels([str(x + 1) for x in trade_labels])
        axis.set_box_aspect(1)
    fig_size = fig.get_size_inches()  # [width (or cols), height (or rows)]
    fig.set_size_inches([2 * fig_size[0], fig_size[1]])
    _ = fig.suptitle("Agent profitability", y=0.88)
    return fig


def get_gridspec_subplots(nrows: int, ncols: int, **kwargs: Any) -> tuple[Figure, Axes, GridSpec]:
    """Setup a figure with axes that have reasonable spacing

    Arguments
    ---------
    nrows : int
       number of rows in the figure
    ncols : int
       number of columns in the figure
    kwargs : Any
        optional keyword arguments to be supplied to matplotlib.gridspec.GridSpec()

    Returns
    ---------
    tuple[Figure, Axes, GridSpec]
        a tuple containing the relevant figure objects
    """
    if "wspace" not in kwargs:
        kwargs["wspace"] = 1.0
    grid_spec = gridspec.GridSpec(nrows, ncols, **kwargs)
    fig = plt.figure()
    axes = [fig.add_subplot(grid_spec[plot_id]) for plot_id in np.ndindex((nrows, ncols))]
    return (fig, axes, grid_spec)


def clear_axis(axis: Axes, spines: str = "none") -> Axes:
    """
    Clear spines & tick labels from proplot axis object

    Arguments
    ---------
        axis : matplotlib axis object
           axis to be cleared
        spines : str
           any matplotlib color, defaults to "none" which makes the spines invisible

    Returns
    ---------
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
    """
    Calls clear_axis iteratively for each axis in axes
    Arguments
    ---------
        axes : list of matplotlib axis objects
           axes to be cleared
        spines : str
           any matplotlib color, defaults to "none" which makes the spines invisible

    Returns
    ---------
        axes : list of matplotlib axis objects
    """
    for axis in axes:
        clear_axis(axis, spines)
    return axes


def format_axis(
    axis_handle, xlabel="", fontsize=18, linestyle="--", linewidth="1", color="grey", which="both", axis="y"
):
    """Formats the axis"""
    # pylint: disable=too-many-arguments
    axis_handle.set_xlabel(xlabel)
    axis_handle.tick_params(axis="both", labelsize=fontsize)
    axis_handle.grid(visible=True, linestyle=linestyle, linewidth=linewidth, color=color, which=which, axis=axis)
    if xlabel == "":
        axis_handle.xaxis.set_ticklabels([])
    axis_handle.legend(fontsize=fontsize)


def annotate(axis_handle, text, major_offset, minor_offset, val):
    """Adds legend-like labels"""
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
        dict(facecolor="white", edgecolor="black", alpha=val["alpha"], linewidth=0, boxstyle="round,pad=0.1")
    )


## Logging
def delete_log_file() -> None:
    """If the logger's handler if a file handler, delete the underlying file."""
    handler = logging.getLogger().handlers[0]
    if isinstance(handler, logging.FileHandler):
        os.remove(handler.baseFilename)
    logging.getLogger().removeHandler(handler)


def setup_logging(
    log_filename: Optional[str] = None,
    max_bytes: int = elfpy.DEFAULT_LOG_MAXBYTES,
    log_level: int = elfpy.DEFAULT_LOG_LEVEL,
) -> None:
    """Setup logging and handlers with default settings"""
    if log_filename is None:
        handler = logging.StreamHandler(sys.stdout)
    else:
        log_dir, log_name = os.path.split(log_filename)
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        handler = RotatingFileHandler(os.path.join(log_dir, log_name), mode="w", maxBytes=max_bytes)
    logging.getLogger().setLevel(log_level)  # events of this level and above will be tracked
    handler.setFormatter(logging.Formatter(elfpy.DEFAULT_LOG_FORMATTER, elfpy.DEFAULT_LOG_DATETIME))
    logging.getLogger().addHandler(handler)  # assign handler to logging


def close_logging(delete_logs=True):
    """Close logging and handlers for the test"""
    logging.shutdown()
    if delete_logs:
        for handler in logging.getLogger().handlers:
            if hasattr(handler, "baseFilename") and not isinstance(handler, logging.StreamHandler):
                # access baseFilename in a type safe way
                handler_file_name = getattr(handler, "baseFilename")
                if os.path.exists(handler_file_name):
                    os.remove(handler_file_name)
            handler.close()


class CustomEncoder(json.JSONEncoder):
    """Custom encoder for JSON string dumps"""

    def default(self, o):
        """Override default behavior"""
        match o:
            case np.integer():
                return int(o)
            case np.floating():
                return float(o)
            case np.ndarray():
                return o.tolist()
            case _:
                try:
                    return o.__dict__
                except AttributeError:
                    return repr(o)
