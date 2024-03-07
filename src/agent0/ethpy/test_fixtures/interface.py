"""Test fixture for deploying local anvil chain and initializing hyperdrive."""

from __future__ import annotations

from typing import Iterator, cast

import pytest
from eth_typing import URI
from web3 import HTTPProvider

from agent0.ethpy.eth_config import EthConfig
from agent0.ethpy.hyperdrive import DeployedHyperdrivePool, HyperdriveAddresses
from agent0.ethpy.hyperdrive.interface import HyperdriveReadInterface, HyperdriveReadWriteInterface

# we need to use the outer name for fixtures
# pylint: disable=redefined-outer-name


def create_hyperdrive_read_interface(_local_hyperdrive_pool: DeployedHyperdrivePool) -> HyperdriveReadInterface:
    """Set up the hyperdrive read interface to access a deployed hyperdrive pool.

    All arguments are fixtures.

    Returns
    -------
        HyperdriveReadInterface
            The interface to access the deployed hyperdrive pool.
    """
    rpc_uri = cast(HTTPProvider, _local_hyperdrive_pool.web3.provider).endpoint_uri or URI("http://localhost:8545")
    hyperdrive_contract_addresses: HyperdriveAddresses = _local_hyperdrive_pool.hyperdrive_contract_addresses
    eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir="./packages/hyperdrive/src/abis")
    return HyperdriveReadInterface(eth_config, addresses=hyperdrive_contract_addresses)


@pytest.fixture(scope="function")
def hyperdrive_read_interface(local_hyperdrive_pool: DeployedHyperdrivePool) -> Iterator[HyperdriveReadInterface]:
    """Fixture representing a hyperdrive read interface to a deployed hyperdrive pool.

    Arguments
    ---------
    local_hyperdrive_pool: DeployedHyperdrivePool
        Fixture representing the deployed hyperdrive pool

    Yields
    ------
    HyperdriveReadInterface
        The interface to access the deployed hyperdrive pool.
    """
    yield create_hyperdrive_read_interface(local_hyperdrive_pool)


def create_hyperdrive_read_write_interface(
    _local_hyperdrive_pool: DeployedHyperdrivePool,
) -> HyperdriveReadWriteInterface:
    """Set up the hyperdrive read write interface to access a deployed hyperdrive pool.

    All arguments are fixtures.

    Returns
    -------
        HyperdriveReadWriteInterface
            The interface to access and write to the deployed hyperdrive pool.
    """
    rpc_uri = cast(HTTPProvider, _local_hyperdrive_pool.web3.provider).endpoint_uri or URI("http://localhost:8545")
    hyperdrive_contract_addresses: HyperdriveAddresses = _local_hyperdrive_pool.hyperdrive_contract_addresses
    eth_config = EthConfig(artifacts_uri="not used", rpc_uri=rpc_uri, abi_dir="./packages/hyperdrive/src/abis")
    return HyperdriveReadWriteInterface(eth_config, addresses=hyperdrive_contract_addresses)


@pytest.fixture(scope="function")
def hyperdrive_read_write_interface(
    local_hyperdrive_pool: DeployedHyperdrivePool,
) -> Iterator[HyperdriveReadWriteInterface]:
    """Fixture representing a hyperdrive interface to a deployed hyperdrive pool.

    Arguments
    ---------
    local_hyperdrive_pool: DeployedHyperdrivePool
        Fixture representing the deployed hyperdrive pool

    Yields
    ------
    HyperdriveReadWriteInterface
        The interface to access and write to the deployed hyperdrive pool.
    """
    yield create_hyperdrive_read_write_interface(local_hyperdrive_pool)
