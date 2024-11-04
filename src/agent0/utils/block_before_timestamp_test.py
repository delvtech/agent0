import numpy as np
import pytest

from agent0 import LocalChain, LocalHyperdrive

from .block_before_timestamp import block_before_timestamp


@pytest.mark.docker
@pytest.mark.anvil
def test_block_before_timestamp(fast_chain_fixture: LocalChain):
    """Test that ensures block_before_timestamp always returns a block number that is closest to but before the timestamp."""

    # Define test constants
    NUM_FUZZ_RUNS = 10_000
    TOLERANCE = 1

    # Advance the chain NUM_FUZZ_RUNS blocks
    initial_block_number = fast_chain_fixture.block_number()
    initial_block_time = fast_chain_fixture.block_number()

    print(f"{initial_block_number=}")
    print(f"{initial_block_time=}")

    fast_chain_fixture.mine_blocks(1)
    initial_block_plus_one_time = fast_chain_fixture.block_time()

    print(f"{initial_block_plus_one_time=}")

    time_between_blocks = initial_block_plus_one_time - initial_block_time
    assert time_between_blocks >= 1
    fast_chain_fixture.mine_blocks(NUM_FUZZ_RUNS - 1)
    chain_block_number = fast_chain_fixture.block_number()
    chain_block_time = fast_chain_fixture.block_time()

    print(f"{chain_block_number=}")
    print(f"{chain_block_time=}")
    print(f"{time_between_blocks=}")

    # Start out a few blocks behind the latest
    hyperdrive_interface = LocalHyperdrive(fast_chain_fixture, LocalHyperdrive.Config()).interface
    for _ in range(NUM_FUZZ_RUNS):
        # Grab a random block in the past & get the time
        test_block_number = int(np.random.randint(initial_block_number + 2, chain_block_number - 1))
        test_block_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_block(test_block_number))

        print(f"{test_block_number=}")
        print(f"{test_block_time=}")

        # Add a random amount of time that is less than the time between blocks
        time_delta = int(np.random.randint(0, time_between_blocks - 1))

        print(f"{time_delta=}")

        # Find the block that was closest to this timestamp
        inferred_block = block_before_timestamp(hyperdrive_interface.web3, test_block_time + time_delta)
        inferred_block_time = hyperdrive_interface.get_block_timestamp(hyperdrive_interface.get_block(inferred_block))

        print(f"{inferred_block=}")
        print(f"{inferred_block_time=}")

        assert (
            inferred_block <= test_block_number
        ), f"Inferred block number = {inferred_block} should be less than or equal to test block number = {test_block_number}."
        assert (
            test_block_number - inferred_block <= TOLERANCE
        ), f"Inferred block number should be within tolerance={TOLERANCE} of test block number."

        test_block_number -= np.random.randint(1, 30)
