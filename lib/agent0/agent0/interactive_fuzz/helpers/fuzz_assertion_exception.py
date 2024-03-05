"""Helper functions for checks and exceptions for fuzz testing."""

from __future__ import annotations

from typing import Any


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
