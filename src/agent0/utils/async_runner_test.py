"""Tests for async_runner."""

import asyncio
from functools import partial

from .async_runner import async_runner


def test_async_runner():
    def _return_int(i: int, j: int) -> tuple[int, int]:
        return (i, j)

    # We set arguments to the function via partials
    partials = [partial(_return_int, i, j=10) for i in range(3)]

    out_tuples = asyncio.run(async_runner(partials, return_exceptions=False))

    for i, o in enumerate(out_tuples):
        assert len(o) == 2
        assert o[0] == i
        assert o[1] == 10
