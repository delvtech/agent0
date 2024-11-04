import numpy as np
import pytest

from agent0 import LocalChain


@pytest.mark.docker
@pytest.mark.anvil
def test_mine_blocks(fast_chain_fixture: LocalChain):
    """Test that ensures block_before_timestamp always returns a block number that is closest to but before the timestamp."""

    time_between_blocks = fast_chain_fixture.config.block_timestamp_interval
    assert time_between_blocks is not None

    NUM_FUZZ_RUNS = 1_000
    previous_block_number = fast_chain_fixture.block_number()
    previous_block_time = fast_chain_fixture.block_time()

    for _ in range(NUM_FUZZ_RUNS):
        num_blocks = np.random.randint(1, 1_000)

        fast_chain_fixture.mine_blocks(num_blocks)

        current_block_number = fast_chain_fixture.block_number()
        current_block_time = fast_chain_fixture.block_time()

        assert (
            current_block_number - previous_block_number == num_blocks
        ), f"{current_block_number-previous_block_number=} != {num_blocks=}"
        assert (
            current_block_time - previous_block_time == num_blocks * time_between_blocks
        ), f"{current_block_time-previous_block_time=} != {num_blocks * time_between_blocks=}"

        previous_block_number = current_block_number
        previous_block_time = current_block_time
