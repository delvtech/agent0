"""Utilities to convert solidity numbers to python numbers"""
from __future__ import annotations

from fixedpoint import FixedPoint


def convert_scaled_value(input_val: int | None) -> float | None:
    """
    Given a scaled value int, converts it to an unscaled value in float, while dealing with Nones

    Arguments
    ----------
    input_val: int | None
        The scaled integer value to unscale and convert to float

    Returns
    -------
    float | None
        The unscaled floating point value

    Note
    ----
    We cast to FixedPoint, then to floats to keep noise to a minimum.
    There is no loss of precision when going from Fixedpoint to float.
    Once this is fed into postgres, postgres will use the fixed-precision Numeric type.
    """
    if input_val is not None:
        return float(FixedPoint(scaled_value=input_val))
    return None
