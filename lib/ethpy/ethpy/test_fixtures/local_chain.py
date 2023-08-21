"""Test fixture for deploying local anvil chain and initializing hyperdrive"""
import subprocess
import time
from typing import Iterator

import pytest
from ethpy.base import initialize_web3_with_http_provider
from ethpy.hyperdrive import HyperdriveAddresses
from web3 import Web3

from .deploy_hyperdrive import deploy_and_initialize_hyperdrive, deploy_hyperdrive_factory, initialize_deploy_account

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name


@pytest.fixture(scope="function")
def local_chain() -> Iterator[str]:
    """Launches a local anvil chain for testing. Kills the anvil chain after.

    Returns
    -------
    Iterator[str]
        Yields the local anvil chain url
    """
    anvil_port = 9999
    host = "127.0.0.1"  # localhost

    # Assuming anvil command is accessible in path
    # running into issue with contract size without --code-size-limit arg

    # Using context manager here seems to make CI hang, so explicitly killing process at the end of yield
    # pylint: disable=consider-using-with
    anvil_process = subprocess.Popen(
        ["anvil", "--host", "127.0.0.1", "--port", str(anvil_port), "--code-size-limit", "9999999999"]
    )

    local_chain_ = "http://" + host + ":" + str(anvil_port)

    # TODO Hack, wait for anvil chain to initialize
    time.sleep(3)

    yield local_chain_

    # Kill anvil process at end
    anvil_process.kill()


@pytest.fixture(scope="function")
def local_hyperdrive_chain(local_chain: str) -> dict:
    """Initializes hyperdrive on a local anvil chain for testing.
    Returns the hyperdrive contract address.

    Arguments
    ---------
    local_chain: str
        The `local_chain` test fixture that binds to the local anvil chain rpc url

    Returns
    -------
    dict
        A dictionary with the following key - value fields:

        "web3": Web3
            web3 provider object
        "deploy_account": LocalAccount
            The local account that deploys and initializes hyperdrive
        "hyperdrive_contract_addresses": HyperdriveAddresses
            The hyperdrive contract addresses
    """
    web3 = initialize_web3_with_http_provider(local_chain, reset_provider=False)
    account = initialize_deploy_account(web3)
    base_token_contract, factory_contract = deploy_hyperdrive_factory(local_chain, account)
    hyperdrive_addr = deploy_and_initialize_hyperdrive(web3, base_token_contract, factory_contract, account)

    return {
        "rpc_url": local_chain,
        "web3": web3,
        "deploy_account": account,
        "hyperdrive_contract_addresses": HyperdriveAddresses(
            base_token=Web3.to_checksum_address(base_token_contract.address),
            hyperdrive_factory=Web3.to_checksum_address(factory_contract.address),
            mock_hyperdrive=Web3.to_checksum_address(hyperdrive_addr),
            mock_hyperdrive_math="not_used",
        ),
    }
