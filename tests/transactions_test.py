"""Test executing transactions."""
# import os
import logging
import time

import pytest
from ethpy.base.errors.errors import ContractCallException
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain

# ruff: noqa: PLR2004 (comparison against magic values (literals like numbers))
# pylint: disable=logging-fstring-interpolation


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
    logging.info("")
    for retry in retries:
        logging.info(f"{retry.created}: {retry.message}")
    attempt_timestamps = [r.created for r in retries]
    diffs = [attempt_timestamps[i + 1] - attempt_timestamps[i] for i in range(len(attempt_timestamps) - 1)]
    diffs = [round(d, 3) for d in diffs]
    logging.info(f"Attempt timestamps: {', '.join([str(ts) for ts in attempt_timestamps])}")
    logging.info(f"diffs: {', '.join([str(d) for d in diffs])}")
    logging.info(f"Total wait time: {sum(diffs):.2f} seconds.")
    logging.info(f"Time to fail: {end_time - start_time:.2f} seconds.")


@pytest.mark.anvil
def test_liquidate(chain: LocalChain):
    """Test liquidation."""
    interactive_hyperdrive = InteractiveHyperdrive(chain)
    alice = interactive_hyperdrive.init_agent(base=FixedPoint(10_000), name="alice")
    alice.open_long(base=FixedPoint(100))
    alice.open_short(bonds=FixedPoint(100))
    alice.add_liquidity(base=FixedPoint(100))
    current_wallet = interactive_hyperdrive.get_current_wallet()
    assert current_wallet.shape[0] == 4  # we have 4 open positions, including base
    alice.liquidate()
    current_wallet = interactive_hyperdrive.get_current_wallet()
    assert current_wallet.shape[0] == 1  # we have 1 open position, including base
