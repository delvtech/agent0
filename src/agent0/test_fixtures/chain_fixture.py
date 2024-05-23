"""Local chain connected to a local database hosted in docker."""

import logging
import os
from pathlib import Path
from typing import Iterator

import docker
import pytest
from docker.errors import DockerException

from agent0.core.hyperdrive.interactive import LocalChain

# Fixtures defined in the same file
# pylint: disable=redefined-outer-name


def launch_chain(port_base) -> LocalChain:
    """Launches a local chain.

    Arguments
    ---------
    port_base: int
        The base port number to use for the chain and database.
        The chain port will be `port_base`, and the database port will be `port_base + 1`.

    Returns
    -------
    LocalChain
        The local chain.
    """
    # Attempt to determine if docker is installed
    try:
        try:
            _ = docker.from_env()
        except Exception:  # pylint: disable=broad-exception-caught
            home_dir = os.path.expanduser("~")
            socket_path = Path(f"{home_dir}") / ".docker" / "desktop" / "docker.sock"
            if socket_path.exists():
                logging.debug("Docker not found at default socket, using %s..", socket_path)
                _ = docker.DockerClient(base_url=f"unix://{socket_path}")
            else:
                logging.debug("Docker not found.")
                _ = docker.from_env()
    # Skip this test if docker isn't installed
    except DockerException as exc:
        # This env variable gets set when running tests in CI
        # Hence, we don't want to skip this test if we're in CI
        in_ci = os.getenv("IN_CI")
        if in_ci is None:
            pytest.skip("Docker engine not found, skipping")
        else:
            raise exc

    local_chain_config = LocalChain.Config(
        chain_port=port_base,
        db_port=port_base + 1,
        # Always preview before trade in tests
        preview_before_trade=True,
    )
    return LocalChain(local_chain_config)


@pytest.fixture(scope="function")
def chain_fixture() -> Iterator[LocalChain]:
    """Local chain connected to a local database hosted in docker.
    This fixture launches a chain from scratch in a function scope.

    Yield
    -----
    LocalChain
        The local chain instance.
    """
    _chain = launch_chain(port_base=20000)
    yield _chain
    _chain.cleanup()
    del _chain


@pytest.fixture(scope="session")
def init_chain() -> Iterator[LocalChain]:
    """Local chain connected to a local database hosted in docker.
    This fixture launches a chain from scratch in a session scope.

    Yield
    -----
    LocalChain
        local chain instance.
    """
    _chain = launch_chain(30000)
    yield _chain
    _chain.cleanup()
    del _chain


@pytest.fixture(scope="function")
def fast_chain_fixture(init_chain: LocalChain) -> Iterator[LocalChain]:
    """Local chain connected to a local database hosted in docker.
    This fixture uses snapshot on an existing chain in a function scope.

    .. note::
        This chain is booted from an existing snapshot for speed.
        If you save a new snapshot the first will be overwritten.

    Arguments
    ---------
    init_chain: LocalChain
        Session scoped chain fixture.

    Yield
    -----
    LocalChain
        Local chain instance.
    """
    init_chain.save_snapshot()
    yield init_chain
    init_chain.load_snapshot()
