"""Formatting utilities to aid in human-readable values."""
from __future__ import annotations  # types will be strings by default in 3.11

import logging

import numpy as np
from fixedpointmath import FixedPoint


def format_numeric_string(value: float | FixedPoint, precision=3, min_digits=0, debug=False):
    """
    Format a float to a string with a given precision.
    This follows the significant figure behavior, irrespective of the number's size.
    """
    if debug:
        log_str = "value: %s, type: %s, precision: %s, min_digits: %s"
        log_vars = (value, type(value), precision, min_digits)
        logging.error(log_str, *log_vars)

    if isinstance(value, FixedPoint):
        value = float(value)

    if np.isinf(value):
        return "inf"
    if np.isnan(value):
        return "nan"
    if value == 0:
        return "0"

    # Calculate the number of digits in value
    try:
        digits = int(np.floor(np.log10(abs(value)))) + 1
    except Exception as err:  # pylint: disable=broad-except
        if debug:
            log_str = "Error in format_numeric_string: value=%s(%s), precision=%s, min_digits=%s, \n error=%s"
            log_vars = (value, type(value), precision, min_digits, err)
            logging.error(log_str, *log_vars)
        return str(value)
    # Sigfigs to the right of the decimal
    decimals = np.clip(precision - digits, min_digits, precision)

    if abs(value) < 0.01 and decimals > precision:
        decimals = precision

    return f"{value:,.{decimals}f}"
