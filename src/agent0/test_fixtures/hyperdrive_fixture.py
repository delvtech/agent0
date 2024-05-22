"""Local chain connected to a local database hosted in docker."""

from typing import Iterator

import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive

from .chain_fixture import launch_chain

# Fixtures defined in the same file
# pylint: disable=redefined-outer-name


def launch_hyperdrive(in_chain: LocalChain) -> LocalHyperdrive:
    """Launches a hyperdrive pool on a given chain.

    Arguments
    ---------
    in_chain: LocalChain
        The chain object.

    Returns
    -------
    LocalHyperdrive
        The deployed hyperdrive object.
    """
    # Initial pool variables
    # NOTE: we set the initial liquidity here to be very small to ensure we can do trades to ensure withdrawal shares
    # Hence, for testing normal conditions, we likely need to increase the initial liquidity by adding
    # liquidity as the first trade of the pool.
    config = LocalHyperdrive.Config(
        initial_liquidity=FixedPoint(1_000),
        # TODO this differs from the default, rework
        # the set of trades to do to ensure withdrawal shares
        # instead of changing the default here
        position_duration=60 * 60 * 24 * 365,  # 1 year
        flat_fee=FixedPoint("0.0005"),
    )
    return LocalHyperdrive(in_chain, config)


@pytest.fixture(scope="function")
def hyperdrive_fixture(chain_fixture: LocalChain) -> LocalHyperdrive:
    """Local hyperdrive pool test fixture.
    This fixture launches a chain from scratch in a function scope.

    Arguments
    ---------
    chain_fixture: LocalChain
        Function scoped chain fixture.

    Returns
    -----
    LocalHyperdrive
        The deployed hyperdrive object.
    """
    return launch_hyperdrive(chain_fixture)


@pytest.fixture(scope="session")
def init_hyperdrive() -> Iterator[LocalHyperdrive]:
    """Local hyperdrive pool test fixture.
    This fixture launches a hyperdrive pool from scratch in a session scope.

    Yield
    -----
    LocalHyperdrive
        The deployed hyperdrive object.
    """
    # Need to launch seperate chain with different port here since
    # the pool itself is going to snapshot.
    # This avoids collisions with the chain fixture.
    _chain = launch_chain(50000)
    yield launch_hyperdrive(_chain)
    _chain.cleanup()
    del _chain


@pytest.fixture(scope="function")
def fast_hyperdrive_fixture(init_hyperdrive: LocalHyperdrive) -> Iterator[LocalHyperdrive]:
    """Local hyperdrive pool test fixture.
    This fixture uses snapshot on an existing chain in a function scope.

    .. note::
        This pool is booted from an existing snapshot for speed.
        If you save a new snapshot the first will be overwritten.

    Arguments
    ---------
    init_hyperdrive: LocalHyperdrive
        Session scoped hyperdrive fixture.

    Yield
    -----
    LocalHyperdrive
        The deployed hyperdrive object.
    """

    init_hyperdrive.chain.save_snapshot()
    yield init_hyperdrive
    init_hyperdrive.chain.load_snapshot()
