"""Test for the block_before_timestamp function."""

import numpy as np
import pytest

from agent0 import LocalChain, LocalHyperdrive

from .block_number_before_timestamp import block_number_before_timestamp


@pytest.mark.docker
@pytest.mark.anvil
def test_block_number_before_timestamp(fast_chain_fixture: LocalChain):
    """Test that ensures block_before_timestamp always returns a block number
    with a timestamp that is closest to but before the provided timestamp.
    """
    # Run the test a bunch of times because the function is iterative.
    num_fuzz_runs = 2_000

    # Advance the chain NUM_FUZZ_RUNS blocks
    initial_block_number = fast_chain_fixture.block_number()
    initial_block_time = fast_chain_fixture.block_time()

    fast_chain_fixture.mine_blocks(1)
    initial_block_plus_one_time = fast_chain_fixture.block_time()

    time_between_blocks = initial_block_plus_one_time - initial_block_time
    assert time_between_blocks >= 1
    fast_chain_fixture.mine_blocks(num_fuzz_runs - 1)
    chain_block_number = fast_chain_fixture.block_number()
    assert chain_block_number == initial_block_number + num_fuzz_runs

    # Start out a few blocks behind the latest
    hyperdrive_interface = LocalHyperdrive(fast_chain_fixture, LocalHyperdrive.Config()).interface
    for fuzz_iter in range(num_fuzz_runs):
        # Grab a random block in the past & get the time
        if fuzz_iter == 0:  # test an edge case on the first iteration
            test_block_number = initial_block_number + 3
        elif fuzz_iter == 1:  # test an edge case on the second iteration
            test_block_number = chain_block_number - 1
        else:
            test_block_number = int(np.random.randint(initial_block_number + 3, chain_block_number - 1))
        test_block_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_block(test_block_number))

        # Add a random amount of time that is less than the time between blocks
        time_delta = int(np.random.randint(0, time_between_blocks))

        # Find the block that was closest to this timestamp
        inferred_block_number = block_number_before_timestamp(hyperdrive_interface.web3, test_block_time + time_delta)
        inferred_block_time = hyperdrive_interface.get_block_timestamp(
            hyperdrive_interface.get_block(inferred_block_number)
        )

        assert (
            inferred_block_number == test_block_number
        ), f"Inferred block number = {inferred_block_number} should be less than or equal to {test_block_number=}."
        assert (
            inferred_block_time <= test_block_time
        ), f"{inferred_block_time=} should be less than or equal to {test_block_time=}."
