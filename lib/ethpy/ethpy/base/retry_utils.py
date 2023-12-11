"""Wrapper functions for retrying."""
from __future__ import annotations

import asyncio
import inspect
import logging
import time
from typing import Awaitable, Callable, ParamSpec, TypeVar

from web3._utils.threads import Timeout

P = ParamSpec("P")
R = TypeVar("R")

# we need lots of arguments for the exponential backoff
# pylint: disable=too-many-arguments
# ruff: noqa: PLR0913


async def async_retry_call(
    retry_count: int,
    retry_exception_check: Callable[[Exception], bool] | None,
    func: Callable[P, Awaitable[R]],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """Retry an async function call.

    Arguments
    ---------
    retry_count: int
        The number of times to retry the function
    retry_exception_check: Callable[[type[Exception]], bool] | None
        A function that takes as an argument an exception and returns True if we want to retry on that exception
        If None, will retry for all exceptions
    func: Callable[P, Awaitable[R]]
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
    timeout = kwargs.pop("timeout", 2)
    start_latency = kwargs.pop("start_latency", 0.01)
    backoff_multiplier = kwargs.pop("backoff_multiplier", 2)
    exception = None
    for attempt_number in range(retry_count):
        try:
            with Timeout(timeout) as _timeout:
                out = await func(*args, **kwargs)
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
            await asyncio.sleep(start_latency * backoff_multiplier**attempt_number)
    assert exception is not None
    raise exception


def retry_call(
    retry_count: int,
    retry_exception_check: Callable[[Exception], bool] | None,
    func: Callable[..., R],
    *args: P.args,
    **kwargs: P.kwargs,
) -> R:
    """Retry a function call.

    Arguments
    ---------
    retry_count: int
        The number of times to retry the function
    retry_exception_check: Callable[[type[Exception]], bool] | None
        A function that takes as an argument an exception and returns True if we want to retry on that exception
        If None, will retry for all exceptions
    func: Callable[P, Awaitable[R]]
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
    # we need lots of arguments for exponential backoff
    # pylint: disable=too-many-arguments
    # TODO can't make a default for `retry_exception_check` due to *args and **kwargs,
    # so we need to explicitly pass in this parameter
    timeout = kwargs.pop("timeout", 2)
    start_latency = kwargs.pop("start_latency", 0.01)
    backoff_multiplier = kwargs.pop("backoff_multiplier", 2)
    exception = None
    for attempt_number in range(retry_count):
        try:
            with Timeout(timeout) as _timeout:
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
            time.sleep(start_latency * backoff_multiplier**attempt_number)
    assert exception is not None
    raise exception
