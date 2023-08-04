"""Useful conversions for database operations."""
from __future__ import annotations

from decimal import Decimal

from fixedpointmath import FixedPoint


def convert_scaled_value_to_decimal(input_val: int | None) -> Decimal | None:
    """
    Given a scaled value int, converts it to a Decimal, while supporting Nones

    Arguments
    ----------
    input_val: int | None
        The scaled integer value to unscale and convert to Decimal

    Returns
    -------
    Decimal | None
        The unscaled Decimal value
    """
    if input_val is not None:
        # TODO add this cast within fixedpoint
        fp_val = FixedPoint(scaled_value=input_val)
        str_val = str(fp_val)
        return Decimal(str_val)
    return None
