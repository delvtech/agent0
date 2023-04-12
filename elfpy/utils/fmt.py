import numpy as np


def fmt(value, precision=3, min_digits=0, debug=False):
    # sourcery skip: assign-if-exp, inline-immediately-returned-variable
    """
    Format a float to a string with a given precision
    this follows the significant figure behavior, irrepective of number size
    """
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
    decimals = np.clip(precision - digits, min_digits, precision)  # sigfigs to the right of the decimal
    if debug:
        print(f"value: {value}, type: {type(value)} calculated digits: {digits}, decimals: {decimals}")
    if abs(value) > 0.01:
        return f"{value:,.{decimals}f}"
    else:  # add an additional sigfig if the value is really small
        return f"{value:0.{precision - 1}e}"
