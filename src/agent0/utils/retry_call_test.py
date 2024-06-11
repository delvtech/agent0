"""Tests for retry calls."""

import pytest

from agent0.core.hyperdrive.interactive import LocalChain

from .retry_call import retry_call


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
