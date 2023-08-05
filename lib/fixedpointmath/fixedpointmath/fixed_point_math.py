"""Math library wrappers that support FixedPoint number format"""
from __future__ import annotations

import math
from typing import TypeVar

from .fixed_point import FixedPoint
from .fixed_point_integer_math import FixedPointIntegerMath

NUMERIC = TypeVar("NUMERIC", FixedPoint, int, float)


# we will use single letter names for the FixedPointMath class since all functions do basic arithmetic
# pylint: disable=invalid-name


class FixedPointMath:
    """Math library that supports FixedPoint arithmetic"""

    @staticmethod
    def clip(x: NUMERIC, minimum: NUMERIC, maximum: NUMERIC) -> NUMERIC:
        """Clip the input, x, to be within (min, max), inclusive"""
        if minimum > maximum:
            raise ValueError(f"{minimum=} must be <= {maximum=}.")
        return FixedPointMath.minimum(FixedPointMath.maximum(x, minimum), maximum)

    @staticmethod
    def maximum(x: NUMERIC, y: NUMERIC) -> NUMERIC:
        """Compare the two inputs and return the greater value.

        If the first argument equals the second, return the first.
        """
        if isinstance(x, FixedPoint) and isinstance(y, FixedPoint):
            if x.is_nan():
                return x
            if y.is_nan():
                return y
        if x >= y:
            return x
        return y

    @staticmethod
    def minimum(x: NUMERIC, y: NUMERIC) -> NUMERIC:
        """Compare the two inputs and return the lesser value.

        If the first argument equals the second, return the first.
        """
        if isinstance(x, FixedPoint) and isinstance(y, FixedPoint):
            if x.is_nan():
                return x
            if y.is_nan():
                return y
        if x <= y:
            return x
        return y

    @staticmethod
    def exp(x: NUMERIC) -> NUMERIC:
        """Performs e^x"""
        if isinstance(x, FixedPoint):
            if not x.is_finite():
                return x
            return FixedPoint(scaled_value=FixedPointIntegerMath.exp(x.scaled_value))
        return type(x)(math.exp(x))

    @staticmethod
    def sqrt(x: NUMERIC) -> NUMERIC:
        """Performs sqrt(x)"""
        return type(x)(math.sqrt(x))
