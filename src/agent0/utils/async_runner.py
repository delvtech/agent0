"""General utility function for running synchronous functions asynchronously."""

from __future__ import annotations

import asyncio
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
