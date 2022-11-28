import numpy as np


def float_to_string(value, precision=3, min_digits=0, debug=False):
    """Format a float to a string with a given precision"""
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
    except:
        if debug:
            print(
                f"Error in float_to_string: value={value}({type(value)}), precision={precision},"
                f" min_digits={min_digits}"
            )
        return str(value)
    decimals = min(max(precision - digits, min_digits), precision)  #  calculate desired decimals
    if debug:
        print(f"value: {value}, type: {type(value)} calculated digits: {digits}, decimals: {decimals}")
    if abs(value) > 0.1:
        string = f"{value:,.{decimals}f}"
    else:
        string = f"{value:0.{precision-1}e}"
    return string
