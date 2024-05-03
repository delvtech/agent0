"""Local chain connected to a local database hosted in docker."""

from typing import Iterator

import pytest
from fixedpointmath import FixedPoint

from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive

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
def init_hyperdrive(init_chain: LocalChain) -> LocalHyperdrive:
    """Local hyperdrive pool test fixture.
    This fixture launches a chain from scratch in a session scope.

    Arguments
    ---------
    init_chain: LocalChain
        Session scoped chain fixture.

    Returns
    -----
    LocalHyperdrive
        The deployed hyperdrive object.
    """
    return launch_hyperdrive(init_chain)


@pytest.fixture(scope="function")
def fast_hyperdrive_fixture(init_hyperdrive: LocalHyperdrive) -> Iterator[LocalHyperdrive]:
    """Local hyperdrive pool test fixture.
    This fixture uses snapshot on an existing chain in a function scope.

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
