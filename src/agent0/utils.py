"""Utility functions."""

from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Callable, ParamSpec, TypeVar

# Async runner helper
P = ParamSpec("P")
R = TypeVar("R")


async def async_runner(
    return_exceptions: bool,
    funcs: list[Callable[P, R]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> list[R]:
    """Helper function that runs a list of passed in functions asynchronously.

    WARNING: this assumes all functions passed in are thread safe, use at your own risk.

    TODO: args and kwargs likely should also be a list for passing in separate arguments.

    Arguments
    ---------
    return_exceptions: bool
        If True, return exceptions from the functions. Otherwise, will throw exception if
        a thread fails.
    funcs: list[Callable[P, R]]
        List of functions to run asynchronously.
    *args: P.args
        Positional arguments for the functions.
    **kwargs: P.kwargs
        Keyword arguments for the functions.

    Returns
    -------
    list[R]
        List of results.
    """
    # We launch all functions in threads using the `to_thread` function.
    # This allows the underlying functions to use non-async waits.

    # Runs all functions passed in and gathers results
    gather_result: list[R | BaseException] = await asyncio.gather(
        *[asyncio.to_thread(func, *args, **kwargs) for func in funcs], return_exceptions=return_exceptions
    )

    # Error checking
    # TODO we can add retries here
    out_result: list[R] = []
    for result in gather_result:
        if isinstance(result, BaseException):
            raise result
        out_result.append(result)

    return out_result


def retry_call(
    retry_count: int,
    retry_exception_check: Callable[[Exception], bool] | None,
    func: Callable[P, R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """Retry a function call to allow for arbitrary RPC failures.

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
