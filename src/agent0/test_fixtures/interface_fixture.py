"""Test fixture for deploying local anvil chain and initializing hyperdrive."""

from __future__ import annotations

import pytest

from agent0.core.hyperdrive.interactive import LocalHyperdrive
from agent0.ethpy.hyperdrive.interface import HyperdriveReadInterface, HyperdriveReadWriteInterface

# we need to use the outer name for fixtures
# pylint: disable=redefined-outer-name


@pytest.fixture(scope="function")
def hyperdrive_read_interface_fixture(fast_hyperdrive_fixture: LocalHyperdrive) -> HyperdriveReadInterface:
    """Fixture representing a hyperdrive read interface to a deployed hyperdrive pool.

    Arguments
    ---------
    fast_hyperdrive_fixture: LocalHyperdrive
        Fixture representing the deployed hyperdrive pool.

    Returns
    ------
    HyperdriveReadInterface
        The interface to access the deployed hyperdrive pool.
    """
    return fast_hyperdrive_fixture.interface.get_read_interface()


@pytest.fixture(scope="function")
def hyperdrive_read_write_interface_fixture(
    fast_hyperdrive_fixture: LocalHyperdrive,
) -> HyperdriveReadWriteInterface:
    """Fixture representing a hyperdrive interface to a deployed hyperdrive pool.

    Arguments
    ---------
    fast_hyperdrive_fixture: LocalHyperdrive
        Fixture representing the deployed hyperdrive pool.

    Returns
    ------
    HyperdriveReadWriteInterface
        The interface to access and write to the deployed hyperdrive pool.
    """
    return fast_hyperdrive_fixture.interface
