"""Tests for convenience functions in the Local Chain."""

import numpy as np
import pytest

from agent0 import LocalChain


@pytest.mark.docker
@pytest.mark.anvil
def test_mine_blocks(fast_chain_fixture: LocalChain):
    """Test that ensures block_before_timestamp always returns a block number
    that is closest to but before the timestamp.
    """

    num_fuzz_runs = 50

    time_between_blocks = fast_chain_fixture.config.block_timestamp_interval
    assert time_between_blocks is not None

    previous_block_number = fast_chain_fixture.block_number()
    previous_block_time = fast_chain_fixture.block_time()

    for _ in range(num_fuzz_runs):
        # Advance the chain a random number of blocks
        num_blocks = np.random.randint(1, 1_000)
        fast_chain_fixture.mine_blocks(num_blocks)

        # Get the new block number and time
        current_block_number = fast_chain_fixture.block_number()
        current_block_time = fast_chain_fixture.block_time()
        avg_time_between_blocks = (current_block_time - previous_block_time) / num_blocks

        # Check that we advanced the blocks correctly
        assert (
            current_block_number - previous_block_number == num_blocks
        ), f"{current_block_number-previous_block_number=} != {num_blocks=}"
        assert (
            current_block_time - previous_block_time == num_blocks * time_between_blocks
        ), f"{current_block_time-previous_block_time=} != {num_blocks * time_between_blocks=}"
        assert avg_time_between_blocks == time_between_blocks, f"{avg_time_between_blocks=} != {time_between_blocks=}"

        previous_block_number = current_block_number
        previous_block_time = current_block_time
