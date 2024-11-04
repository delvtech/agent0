import numpy as np
import pytest

from agent0 import LocalChain, LocalHyperdrive

from .block_before_timestamp import block_before_timestamp


@pytest.mark.docker
@pytest.mark.anvil
def test_block_before_timestamp(fast_chain_fixture: LocalChain):
    """Test that ensures block_before_timestamp always returns a block number that is closest to but before the timestamp."""

    # Define test constants
    MAX_BLOCK_DECREMENT = 30
    NUM_FUZZ_RUNS = 10_000
    TOLERANCE = 1

    # Advance time to get some blocks
    fast_chain_fixture.mine_blocks(NUM_FUZZ_RUNS * MAX_BLOCK_DECREMENT)
    fast_chain_fixture.block_number()

    # Start out a few blocks behind the latest
    test_block_number = fast_chain_fixture.block_number() - 3
    assert test_block_number > 0
    hyperdrive_interface = LocalHyperdrive(fast_chain_fixture, LocalHyperdrive.Config()).interface
    for _ in range(NUM_FUZZ_RUNS):
        block_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_block(test_block_number))
        approx_block = block_before_timestamp(hyperdrive_interface.web3, block_time)

        assert (
            approx_block <= test_block_number
        ), "Approximate block number should be less than or equal to test block number."
        assert (
            test_block_number - approx_block <= TOLERANCE
        ), f"Approximate block number should be within tolerance={TOLERANCE} of test block number."

        test_block_number -= np.random.randint(1, 30)
