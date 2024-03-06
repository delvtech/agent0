"""Test fixture for deploying local anvil chain and initializing hyperdrive."""

from __future__ import annotations

import subprocess
import time
from typing import Iterator

import pytest

# we need to use the outer name for fixtures
# pylint: disable=redefined-outer-name


def launch_local_chain(anvil_port: int = 9999, host: str = "127.0.0.1") -> Iterator[str]:
    """Launch a local anvil chain.

    Arguments
    ---------
    anvil_port: int
        Port number for the anvil chain.
    host: str
        Host address.

    Yields
    ------
    str
        The local anvil chain URI.
    """
    # Supress output of anvil
    anvil_process = subprocess.Popen(  # pylint: disable=consider-using-with
        ["anvil", "--host", host, "--port", str(anvil_port), "--code-size-limit", "9999999999"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.STDOUT,
    )
    time.sleep(3)  # Wait for anvil chain to initialize

    yield f"http://{host}:{anvil_port}"
    anvil_process.kill()  # Kill anvil process at end


@pytest.fixture(scope="session")
def local_chain() -> Iterator[str]:
    """Fixture representing a local anvil chain.
    This fixture is session scoped, so each test will deploy its own pool for testing.

    Yields
    ------
    str
        The local anvil chain URI.
    """
    yield from launch_local_chain()
