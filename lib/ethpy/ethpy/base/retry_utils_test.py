"""Test executing transactions."""

import pytest
from ethpy.base import retry_call
from ethpy.hyperdrive.interface import HyperdriveReadInterface


@pytest.mark.anvil
def test_retry_call_success(hyperdrive_read_interface: HyperdriveReadInterface, caplog: pytest.LogCaptureFixture):
    """Verify that a bogus call produces the correct number of retries."""
    retry_count = 5
    # getting the block should always work
    _ = retry_call(retry_count, None, hyperdrive_read_interface.web3.eth.get_block, "latest", full_transactions=True)
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
