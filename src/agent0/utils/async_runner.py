"""General utility function for running synchronous functions asynchronously."""

from __future__ import annotations

import asyncio
from concurrent.futures import ThreadPoolExecutor
from typing import Callable, Sequence, TypeVar

# Async runner helper
R = TypeVar("R")


async def async_runner(
    funcs: Sequence[Callable[[], R]],
    return_exceptions: bool = False,
) -> list[R]:
    """Helper function that runs a list of passed in functions asynchronously.

    NOTE: use `functools.partial()` to pass in arguments to the functions.

    WARNING: this assumes all functions passed in are thread safe, use at your own risk.

    Arguments
    ---------
    funcs: list[Callable[[], R]]
        List of functions to run asynchronously.
    return_exceptions: bool
        If True, return exceptions from the functions. Otherwise, will throw exception if
        a thread fails.

    Returns
    -------
    list[R]
        List of results.
    """
    # We launch all functions in threads using the `to_thread` function.
    # This allows the underlying functions to use non-async waits.
    loop = asyncio.get_running_loop()

    # NOTE if the underlying funcs is doing a long non-async wait,
    # the number of executions can be limited based on the number of available
    # threads on the machine.
    with ThreadPoolExecutor() as pool:
        # Runs all functions passed in and gathers results
        gather_result: list[R | BaseException] = await asyncio.gather(
            *[loop.run_in_executor(pool, func) for func in funcs], return_exceptions=return_exceptions
        )

    # Error checking
    # TODO we can add retries here
    out_result: list[R] = []
    for result in gather_result:
        if isinstance(result, BaseException):
            raise result
        out_result.append(result)

    return out_result
