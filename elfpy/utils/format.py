import logging

import numpy as np


def format_float_as_string(value, precision=3, min_digits=0, debug=False):
    """
    Format a float to a string with a given precision
    this follows the significant figure behavior, irrepective of number size
    """
    if debug:
        log_str = "value: {}, type: {}, precision: {}, min_digits: {}"
        log_vars = value, type(value), precision, min_digits
        logging.error(log_str, *log_vars)
    if isinstance(value, float):  # only floats can be inf or nan
        if np.isinf(value):
            return "inf"
        if np.isnan(value):
            return "nan"
    if value == 0:
        return "0"
    try:
        digits = int(np.floor(np.log10(abs(value)))) + 1  #  calculate number of digits in value
    except Exception as err:  # pylint: disable=broad-exception-caught
        if debug:
            log_str = "Error in float_to_string: value={}({}), precision={}, min_digits={}, \n error={}"
            log_vars = value, type(value), precision, min_digits, err
            logging.error(log_str, *log_vars)
        return str(value)
    decimals = np.clip(precision - digits, min_digits, precision)  # sigfigs to the right of the decimal
    if debug:
        log_str = "value: {}, type: {}, precision: {}, min_digits: {}"
        log_vars = value, type(value), precision, min_digits
        logging.error(log_str, *log_vars)
    if abs(value) > 0.01:
        return f"{value:,.{decimals}f}"
    return f"{value:0.{precision - 1}e}"
