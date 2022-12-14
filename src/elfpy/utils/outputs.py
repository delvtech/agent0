"""
Helper functions for post-processing simulation outputs
"""
import os
import json
import logging
from logging.handlers import RotatingFileHandler

import numpy as np

import elfpy


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


def float_to_string(value, precision=3, min_digits=0, debug=False):
    """
    Format a float to a string with a given precision
    this follows the significant figure behavior, irrepective of number size
    """
    # TODO: Include more specific error handling in the except statement
    # pylint: disable=broad-except
    if debug:
        print(f"value: {value}, type: {type(value)}, precision: {precision}, min_digits: {min_digits}")
    if np.isinf(value):
        return "inf"
    if np.isnan(value):
        return "nan"
    if value == 0:
        return "0"
    try:
        digits = int(np.floor(np.log10(abs(value)))) + 1  #  calculate number of digits in value
    except Exception as err:
        if debug:
            print(
                f"Error in float_to_string: value={value}({type(value)}), precision={precision},"
                f" min_digits={min_digits}, \n error={err}"
            )
        return str(value)
    # decimals = np.clip(precision - digits, 0, precision)
    decimals = min(max(precision - digits, min_digits), precision)  #  calculate desired decimals
    if debug:
        print(f"value: {value}, type: {type(value)} calculated digits: {digits}, decimals: {decimals}")
    if abs(value) > 0.1:
        string = f"{value:,.{decimals}f}"
    else:  # add an additional sigfig if the value is really small
        string = f"{value:0.{precision-1}e}"
    return string


def setup_logging(log_dir: str, log_name: str) -> None:
    """Setup logging and handlers with default settings"""
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    handler = RotatingFileHandler(os.path.join(log_dir, log_name), mode="w", maxBytes=elfpy.DEFAULT_LOG_MAXBYTES)
    logging.getLogger().setLevel(elfpy.DEFAULT_LOG_LEVEL)  # events of this level and above will be tracked
    handler.setFormatter(logging.Formatter(elfpy.DEFAULT_LOG_FORMATTER, elfpy.DEFAULT_LOG_DATETIME))
    logging.getLogger().handlers = [
        handler,
    ]


class CustomEncoder(json.JSONEncoder):
    def default(self, obj):
        match obj:
            case np.integer():
                return int(obj)
            case np.floating():
                return float(obj)
            case np.ndarray():
                return obj.tolist()
            case _:
                try:
                    return obj.__dict__
                except AttributeError as e:
                    raise AttributeError(e)
