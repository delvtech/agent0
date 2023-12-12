"""Test executing transactions."""
import logging
import time

import pytest
from ethpy.base import retry_call
from ethpy.base.errors.errors import ContractCallException
from ethpy.hyperdrive.interface import HyperdriveInterface
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive

# ruff: noqa: PLR2004 (comparison against magic values (literals like numbers))


@pytest.mark.anvil
def test_retry_call_success(interface: HyperdriveInterface, caplog: pytest.LogCaptureFixture):
    """Verify that a bogus call produces the correct number of retries."""
    retry_count = 5
    # getting the block should always work
    successful_return = retry_call(retry_count, None, interface.web3.eth.get_block, "latest", full_transactions=True)
    retries = [r for r in caplog.records if r.message.startswith("Retry")]
    assert len(retries) == 0


@pytest.mark.anvil
def test_retry_call_success(interface: HyperdriveInterface, caplog: pytest.LogCaptureFixture):
    """Verify that a bogus call produces the correct number of retries."""
    for read_retry_count in [0, 1, 4]:
        # getting the block should always work
        successful_return = retry_call(
            read_retry_count, None, interface.web3.eth.get_block, "latest", full_transactions=True
        )
        retries = [r for r in caplog.records if r.message.startswith("Retry")]
        assert len(retries) == 0

    interactive_hyperdrive = InteractiveHyperdrive(chain)
    larry = interactive_hyperdrive.init_agent(base=FixedPoint(100), name="larry")
    # This should fail
    start_time = time.time()
    with pytest.raises(ContractCallException):
        larry.remove_liquidity(shares=FixedPoint(20))
    end_time = time.time()
    # Check the captured log messages
    retries = [r for r in caplog.records if r.message.startswith("Retry")]
    assert len(retries) == 5
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
