import numpy as np

def fmt(value, precision=3, min_digits=0):
    if np.isinf(value):
        return "inf"
    if np.isnan(value):
        return "nan"
    if value == 0:
        return "0"
    try:
        digits = int(np.floor(np.log10(abs(value)))) + 1 #  calculate number of digits in value
    except:
        return str(value)
    decimals = min(max(precision-digits,min_digits),precision) #  calculate desired decimals
    if abs(value) > 0.1:
        string = f"{value:,.{decimals}f}"
    else:
        string = f"{value:.{precision-1}e}"
    return string