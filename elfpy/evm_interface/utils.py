"""Utilities for contract interfaces"""
from __future__ import annotations

from fixedpointmath import FixedPoint


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
    """
    # We cast to FixedPoint, then to floats to keep noise to a minimum
    # This is assuming there's no loss of precision going from Fixedpoint to float
    # Once this gets fed into postgres, postgres has fixed precision Numeric type
    if input is not None:
        return float(FixedPoint(scaled_value=input_val))
    return None
