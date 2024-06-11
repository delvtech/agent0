"""Tests for async_runner."""

import asyncio
from functools import partial

from .async_runner import async_runner


def test_async_runner():
    def _return_int(i: int, j: int) -> tuple[int, int]:
        return (i, j)

    # TODO because _async_runner only takes one set of arguments for all calls,
    # we make partial calls for each call. The proper fix here is to generalize
    # _async_runner to take separate arguments for each call.
    partials = [partial(_return_int, i) for i in range(3)]

    out_tuples = asyncio.run(async_runner(return_exceptions=False, funcs=partials, j=10))

    for i, o in enumerate(out_tuples):
        assert len(o) == 2
        assert o[0] == i
        assert o[1] == 10
