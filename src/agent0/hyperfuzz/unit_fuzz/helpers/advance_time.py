"""Helpers for advancing time wrt checkpoint boundaries"""

from numpy.random import Generator

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive


def advance_time_before_checkpoint(chain: LocalChain, rng: Generator, interactive_hyperdrive: LocalHyperdrive) -> None:
    """Advance time on the chain a random amount that is less than the next checkpoint time.

    Arguments
    ---------
    chain: LocalChain
        An instantiated LocalChain.
    rng: `Generator <https://numpy.org/doc/stable/reference/random/generator.html>`_
        The numpy Generator provides access to a wide range of distributions, and stores the random state.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    """

    current_block_time = interactive_hyperdrive.interface.get_block_timestamp(
        interactive_hyperdrive.interface.get_current_block()
    )
    time_since_last_checkpoint = current_block_time % interactive_hyperdrive.interface.pool_config.checkpoint_duration
    time_to_next_checkpoint = (
        interactive_hyperdrive.interface.pool_config.checkpoint_duration - time_since_last_checkpoint
    )
    advance_upper_bound = time_to_next_checkpoint - 100  # minus 100 seconds to avoid edge cases

    # If we're already within the boundary of the next checkpoint, we throw an error
    if advance_upper_bound < 0:
        raise AssertionError("Advance time before checkpoint already too close to checkpoint boundary")

    checkpoint_info = chain.advance_time(
        rng.integers(low=0, high=advance_upper_bound),
        create_checkpoints=True,  # we don't want to create one, but only because we haven't advanced enough
    )
    # Do a final check to make sure that the checkpoint didn't happen
    assert len(checkpoint_info[interactive_hyperdrive]) == 0, "Checkpoint was created when it should not have been."


def advance_time_after_checkpoint(chain: LocalChain, interactive_hyperdrive: LocalHyperdrive) -> None:
    """Advance time on the chain to the next checkpoint boundary plus some buffer.

    Arguments
    ---------
    chain: LocalChain
        An instantiated LocalChain.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    """
    # Advance enough time to make sure we're not going to cross a boundary during our trades
    current_block_time = interactive_hyperdrive.interface.get_block_timestamp(
        interactive_hyperdrive.interface.get_current_block()
    )
    time_since_last_checkpoint = current_block_time % interactive_hyperdrive.interface.pool_config.checkpoint_duration
    time_to_next_checkpoint = (
        interactive_hyperdrive.interface.pool_config.checkpoint_duration - time_since_last_checkpoint
    )

    # Add a small amount to ensure we're not at the edge of a checkpoint
    chain.advance_time(time_to_next_checkpoint + 100, create_checkpoints=True)
