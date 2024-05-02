"""Local chain connected to a local database hosted in docker."""

import logging
import os
from pathlib import Path
from typing import Iterator

import docker
import pytest
from docker.errors import DockerException

from agent0.core.hyperdrive.interactive import LocalChain


@pytest.fixture(scope="session")
def init_chain() -> Iterator[LocalChain]:
    """Local chain connected to a local database hosted in docker.

    Yield
    -----
    LocalChain
        local chain instance.
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

    local_chain_config = LocalChain.Config()
    _chain = LocalChain(local_chain_config)
    yield _chain
    _chain.cleanup()


@pytest.fixture(scope="function")
def chain(init_chain: LocalChain) -> Iterator[LocalChain]:

    init_chain.save_snapshot()
    yield init_chain
    init_chain.load_snapshot()
