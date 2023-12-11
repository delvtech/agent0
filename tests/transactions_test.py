"""Test executing transactions."""
# import os
import time

import pytest
from ethpy.base.errors.errors import ContractCallException
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain

# ruff: noqa: PLR2004 (comparison against magic values (literals like numbers))


@pytest.mark.anvil
def test_retry_call(chain: LocalChain, caplog: pytest.LogCaptureFixture):
    """Retry a bogus call."""
    interactive_hyperdrive = InteractiveHyperdrive(chain)
    larry = interactive_hyperdrive.init_agent(base=FixedPoint(100), name="larry")
    # os.environ["_PYTEST_RAISE"] = "0"  # let pytest raise exceptions
    # This should fail
    start_time = time.time()
    with pytest.raises(ContractCallException):
        larry.remove_liquidity(shares=FixedPoint(20))
    end_time = time.time()
    # Check the captured log messages
    retries = [r for r in caplog.records if r.message.startswith("Retry")]
    assert len(retries) == 5
    print("")
    for retry in retries:
        print(f"{retry.created}: {retry.message}")
    attempt_timestamps = [r.created for r in retries]
    diffs = [attempt_timestamps[i + 1] - attempt_timestamps[i] for i in range(len(attempt_timestamps) - 1)]
    diffs = [round(d, 3) for d in diffs]
    print(f"Attempt timestamps: {', '.join([str(ts) for ts in attempt_timestamps])}")
    print(f"diffs: {', '.join([str(d) for d in diffs])}")
    print(f"Total wait time: {sum(diffs):.2f} seconds.")
    print(f"Time to fail: {end_time - start_time:.2f} seconds.")
