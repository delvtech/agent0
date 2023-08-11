"""Test fixture for deploying local anvil chain and initializing hyperdrive"""
import subprocess
import time
from typing import Any, Generator

import pytest
from ethpy.base import initialize_web3_with_http_provider

from .deploy_hyperdrive import deploy_and_initialize_hyperdrive, deploy_hyperdrive_factory, initialize_deploy_account

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name


@pytest.fixture(scope="function")
def local_chain() -> Generator[str, Any, Any]:
    """Launches a local anvil chain for testing.
    Returns the chain url.
    """
    anvil_port = 9999
    host = "127.0.0.1"  # localhost

    # Assuming anvil command is accessable in path
    # running into issue with contract size without --code-size-limit arg
    with subprocess.Popen(
        ["anvil", "--host", "127.0.0.1", "--port", str(anvil_port), "--code-size-limit", "9999999999"]
    ):
        local_chain_ = "http://" + host + ":" + str(anvil_port)

        # Hack, wait for anvil chain to initialize
        time.sleep(3)

        yield local_chain_

    # Context manager should handle closing the subprocess


@pytest.fixture(scope="function")
def hyperdrive_contract_address(local_chain: str) -> str:
    """Initializes hyperdrive on a local anvil chain for testing.
    Returns the hyperdrive contract address.

    """
    web3 = initialize_web3_with_http_provider(local_chain, reset_provider=False)
    account = initialize_deploy_account(web3)
    base_token_contract, factory_contract = deploy_hyperdrive_factory(local_chain, account)
    return deploy_and_initialize_hyperdrive(web3, base_token_contract, factory_contract, account)
