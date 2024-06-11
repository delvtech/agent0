"""General utility function for retrying a function call."""

from __future__ import annotations

import inspect
import logging
import time
from typing import Callable, ParamSpec, TypeVar

# Async runner helper
P = ParamSpec("P")
R = TypeVar("R")


def retry_call(
    retry_count: int,
    retry_exception_check: Callable[[Exception], bool] | None,
    func: Callable[P, R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """Retry a function call to allow for arbitrary failures.

    Arguments
    ---------
    retry_count: int
        The number of times to retry the function. Must be > 0.
    retry_exception_check: Callable[[type[Exception]], bool] | None
        A function that takes as an argument an exception and returns True if we want to retry on that exception
        If None, will retry for all exceptions
    func: Callable[P, R]
        The function to call.
    *args: P.args
        The positional arguments to call func with
    **kwargs: P.kwargs
        The keyword arguments to call the func with

    Returns
    -------
    R
        Returns the value of the called function
    """
    # TODO can't make a default for `retry_exception_check` due to *args and **kwargs,
    # so we need to explicitly pass in this parameter
    if retry_count <= 0:
        raise ValueError("retry_count must be greater than zero.")
    exception = None
    for attempt_number in range(retry_count):
        try:
            out = func(*args, **kwargs)
            return out
        # Catching general exception but throwing if fails
        except Exception as exc:  # pylint: disable=broad-exception-caught
            # Raise exception immediately if exception check fails
            if retry_exception_check is not None and not retry_exception_check(exc):
                raise exc
            # Get caller of this function's name
            caller = inspect.stack()[1][3]
            logging.warning(
                "Retry attempt %s out of %s: Function %s called from %s failed with %s",
                attempt_number + 1,
                retry_count,
                func,
                caller,
                repr(exc),
            )
            exception = exc
            time.sleep(0.1)
    assert exception is not None
    raise exception
