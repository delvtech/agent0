"""Test executing transactions."""
import logging
import time

import pytest
from ethpy.base import retry_call
from ethpy.base.errors.errors import ContractCallException
from ethpy.hyperdrive.interface import HyperdriveInterface
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain


@pytest.mark.anvil
def test_retry_call_success(hyperdrive_interface: HyperdriveInterface, caplog: pytest.LogCaptureFixture):
    """Verify that a bogus call produces the correct number of retries."""
    retry_count = 5
    # getting the block should always work
    _ = retry_call(retry_count, None, hyperdrive_interface.web3.eth.get_block, "latest", full_transactions=True)
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


@pytest.mark.anvil
def test_retry_hyperdrive_action(chain: LocalChain, caplog: pytest.LogCaptureFixture):
    # TODO: We should not be hard-coding this so often, but at least this test will break if we change the value.
    num_retries = 5
    interactive_hyperdrive = InteractiveHyperdrive(chain)
    larry = interactive_hyperdrive.init_agent(base=FixedPoint(100), name="larry")
    # This should fail, larry has no liquidity
    start_time = time.time()
    with pytest.raises(ContractCallException):
        larry.remove_liquidity(shares=FixedPoint(20))
    end_time = time.time()
    # Check the captured log messages
    retries = [r for r in caplog.records if r.message.startswith("Retry")]
    assert len(retries) == num_retries
    logging.info("")
    for retry in retries:
        logging.info("%s: %s", retry.created, retry.message)
    attempt_timestamps = [r.created for r in retries]
    diffs = [attempt_timestamps[i + 1] - attempt_timestamps[i] for i in range(len(attempt_timestamps) - 1)]
    diffs = [round(d, 3) for d in diffs]
    logging.info("Attempt timestamps: %s", ", ".join([str(ts) for ts in attempt_timestamps]))
    logging.info("diffs: %s", ", ".join([str(d) for d in diffs]))
    logging.info("Total wait time: %2f seconds.", sum(diffs))
    logging.info("Time to fail: %2f seconds.", end_time - start_time)
