"""Test executing transactions."""

import asyncio
from functools import partial

import pytest

from agent0.core.hyperdrive.interactive import LocalChain

from .utils import async_runner, retry_call


def test_async_runner():
    def _return_int(i: int, j: int) -> tuple[int, int]:
        return (i, j)

    # TODO because _async_runner only takes one set of arguments for all calls,
    # we make partial calls for each call. The proper fix here is to generalize
    # _async_runner to take separate arguments for each call.
    partials = [partial(_return_int, i) for i in [1, 2, 3]]

    out_tuples = asyncio.run(async_runner(return_exceptions=False, funcs=partials, j=10))

    for i, o in enumerate(out_tuples):
        assert len(o) == 2
        assert o[0] == i
        assert o[1] == 10


@pytest.mark.anvil
def test_retry_call_success(fast_chain_fixture: LocalChain, caplog: pytest.LogCaptureFixture):
    """Verify that a bogus call produces the correct number of retries."""
    retry_count = 5
    # getting the block should always work

    web3 = fast_chain_fixture._web3  # pylint: disable=protected-access

    _ = retry_call(retry_count, None, web3.eth.get_block, "latest", full_transactions=True)
    retries = [r for r in caplog.records if r.message.startswith("Retry")]
    assert len(retries) == 0


@pytest.mark.anvil
def test_retry_call_fail(caplog: pytest.LogCaptureFixture):
    """Verify that a bogus call produces the correct number of retries."""

    def fail_func():
        raise AssertionError("Failed function")

    with pytest.raises(ValueError):
        _ = retry_call(0, None, fail_func)

    for read_retry_count in [1, 4, 8]:
        # getting the block should always work
        with pytest.raises(AssertionError):
            _ = retry_call(read_retry_count, None, fail_func)
        retries = [r for r in caplog.records if r.message.startswith("Retry")]
        assert len(retries) == read_retry_count
        caplog.clear()
