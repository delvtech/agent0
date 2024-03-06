"""Test executing transactions."""

from typing import cast

import pytest
from eth_typing import URI
from web3 import HTTPProvider

from agent0.ethpy.base import initialize_web3_with_http_provider, retry_call
from agent0.ethpy.test_fixtures import DeployedHyperdrivePool


@pytest.mark.anvil
def test_retry_call_success(local_hyperdrive_pool: DeployedHyperdrivePool, caplog: pytest.LogCaptureFixture):
    """Verify that a bogus call produces the correct number of retries."""
    retry_count = 5
    # getting the block should always work
    rpc_uri = cast(HTTPProvider, local_hyperdrive_pool.web3.provider).endpoint_uri or URI("http://localhost:8545")
    web3 = initialize_web3_with_http_provider(rpc_uri)
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
