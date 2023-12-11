"""Helper functions for checks and exceptions for fuzz testing."""
from __future__ import annotations

from typing import Any

from fixedpointmath import FixedPoint


def fp_isclose(a: FixedPoint, b: FixedPoint, abs_tol: FixedPoint = FixedPoint("0.0")) -> bool:
    """Fixed point isclose function. Ignores relative tolerance since FixedPoint should be accurate regardless
    of scale.

    Arguments
    ---------
    a: FixedPoint
        The first number to compare
    b: FixedPoint
        The second number to compare
    abs_tol: FixedPoint, optional
        The absolute tolerance. Defaults to requiring a and b to be exact.

    Returns
    -------
    bool
        Whether or not the numbers are close
    """
    if abs(a - b) <= abs_tol:
        return True
    return False


class FuzzAssertionException(Exception):
    """Custom exception to throw when fuzz testing assertion fails, adds additional data to the exception."""

    def __init__(
        self,
        *args,
        # Explicitly passing these arguments as kwargs to allow for multiple `args` to be passed in
        # similar for other types of exceptions
        exception_data: dict[str, Any] | None = None,
    ):
        super().__init__(*args)
        if exception_data is None:
            exception_data = {}
        self.exception_data = exception_data
