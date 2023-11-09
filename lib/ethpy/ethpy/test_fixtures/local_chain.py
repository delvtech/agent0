"""Test fixture for deploying local anvil chain and initializing hyperdrive."""
from __future__ import annotations

import subprocess
import time
from typing import Iterator

import pytest
from fixedpointmath import FixedPoint
from hypertypes.IHyperdriveTypes import Fees, PoolConfig

from ethpy.hyperdrive import DeployedHyperdrivePool, deploy_hyperdrive_from_factory


def launch_local_chain(anvil_port: int = 9999, host: str = "127.0.0.1"):
    """Launch a local anvil chain.

    Parameters
    ----------
    anvil_port : int
        Port number for the anvil chain.
    host : str
        Host address.

    Yields
    ------
    str
        The local anvil chain URI.
    """
    anvil_process = subprocess.Popen(
        ["anvil", "--host", host, "--port", str(anvil_port), "--code-size-limit", "9999999999"]
    )
    time.sleep(3)  # Wait for anvil chain to initialize

    yield f"http://{host}:{anvil_port}"
    anvil_process.kill()  # Kill anvil process at end


@pytest.fixture(scope="function")
def local_chain() -> Iterator[str]:
    """Fixture representing a local anvil chain.

    Yields
    ------
    str
        The local anvil chain URI.
    """
    yield from launch_local_chain()


@pytest.fixture(scope="function")
def local_hyperdrive_pool(local_chain_uri: str) -> DeployedHyperdrivePool:
    """Fixture representing a deployed local hyperdrive pool.

    Arguments
    ---------
    local_chain_uri: str
        The URI to chain to deploy on.

    Returns
    -------
    LocalHyperdriveChain
        A tuple with the following key - value fields:

        web3: Web3
            web3 provider object
        deploy_account: LocalAccount
            The local account that deploys and initializes hyperdrive
        hyperdrive_contract_addresses: HyperdriveAddresses
            The hyperdrive contract addresses
        hyperdrive_contract : Contract
            web3.py contract instance for the hyperdrive contract
        hyperdrive_factory_contract : Contract
            web3.py contract instance for the hyperdrive factory contract
        base_token_contract : Contract
            web3.py contract instance for the base token contract
    """
    return launch_local_hyperdrive_pool(local_chain_uri)


def launch_local_hyperdrive_pool(
    local_chain_uri: str,
) -> DeployedHyperdrivePool:  # pylint: disable=redefined-outer-name
    """Initialize hyperdrive on a local chain for testing.

    Arguments
    ---------
    local_chain_uri: str
        The URI to chain to deploy on.

    Returns
    -------
    LocalHyperdriveChain
        A tuple with the following key - value fields:

        web3: Web3
            web3 provider object
        deploy_account: LocalAccount
            The local account that deploys and initializes hyperdrive
        hyperdrive_contract_addresses: HyperdriveAddresses
            The hyperdrive contract addresses
        hyperdrive_contract : Contract
            web3.py contract instance for the hyperdrive contract
        hyperdrive_factory_contract : Contract
            web3.py contract instance for the hyperdrive factory contract
        base_token_contract : Contract
            web3.py contract instance for the base token contract
    """
    # Lots of local  variables for the tests
    # pylint: disable=too-many-locals
    # Deployer is the pre-funded account on the Delv devnet
    deployer_private_key: str = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    # ABI folder should contain JSON and Bytecode files for the following contracts:
    # ERC20Mintable, MockERC4626, ForwarderFactory, ERC4626HyperdriveDeployer, ERC4626HyperdriveFactory
    abi_folder = "packages/hyperdrive/src/abis/"
    # Factory initializaiton parameters
    initial_variable_rate = FixedPoint("0.05")
    curve_fee = FixedPoint("0.1")  # 10%
    flat_fee = FixedPoint("0.0005")  # 0.05%
    governance_fee = FixedPoint("0.15")  # 15%
    max_curve_fee = FixedPoint("0.3")  # 30%
    max_flat_fee = FixedPoint("0.0015")  # 0.15%
    max_governance_fee = FixedPoint("0.30")  # 30%
    fees = Fees(curve_fee.scaled_value, flat_fee.scaled_value, governance_fee.scaled_value)
    max_fees = Fees(max_curve_fee.scaled_value, max_flat_fee.scaled_value, max_governance_fee.scaled_value)
    # Pool initialization parameters
    initial_fixed_rate = FixedPoint("0.05")  # 5%
    initial_liquidity = FixedPoint(100_000_000)
    initial_share_price = FixedPoint(1)
    minimum_share_reserves = FixedPoint(10)
    minimum_transaction_amount = FixedPoint("0.001")
    position_duration = 604800  # 1 week
    checkpoint_duration = 3600  # 1 hour
    time_stretch = FixedPoint(1) / (
        FixedPoint("5.24592") / (FixedPoint("0.04665") * (initial_fixed_rate * FixedPoint(100)))
    )
    oracle_size = 10
    update_gap = 3600  # 1 hour
    pool_config = PoolConfig(
        "",  # will be determined in the deploy function
        initial_share_price.scaled_value,
        minimum_share_reserves.scaled_value,
        minimum_transaction_amount.scaled_value,
        position_duration,
        checkpoint_duration,
        time_stretch.scaled_value,
        "",  # will be determined in the deploy function
        "",  # will be determined in the deploy function
        fees,
        oracle_size,
        update_gap,
    )
    return deploy_hyperdrive_from_factory(
        local_chain_uri,
        abi_folder,
        deployer_private_key,
        initial_liquidity,
        initial_variable_rate,
        initial_fixed_rate,
        pool_config,
        max_fees,
    )
