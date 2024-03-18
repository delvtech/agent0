"""Test fixture for deploying local anvil chain and initializing hyperdrive."""

from __future__ import annotations

from typing import Callable, Iterator

import pytest
from fixedpointmath import FixedPoint
from web3.types import RPCEndpoint

from agent0.ethpy.base import initialize_web3_with_http_provider
from agent0.ethpy.hyperdrive import DeployedHyperdrivePool, deploy_hyperdrive_from_factory
from agent0.hypertypes import FactoryConfig, Fees, PoolDeployConfig

# we need to use the outer name for fixtures
# pylint: disable=redefined-outer-name


@pytest.fixture(scope="session")
def init_local_hyperdrive_pool(
    local_chain: str,
) -> tuple[DeployedHyperdrivePool, Callable[[], str], Callable[[str], None]]:
    """Fixture representing a deployed local hyperdrive pool.

    Arguments
    ---------
    local_chain: str
        Fixture representing a local anvil chain.

    Returns
    -------
    DeployedHyperdrivePool, Callable[[], str], Callable[[str], None]
        The various parameters for a deployed pool, a snapshot function, and a reset function
    """
    # pylint: disable=redefined-outer-name
    out = launch_local_hyperdrive_pool(local_chain)
    # Save the state for the pool and return for this fixture

    _w3 = initialize_web3_with_http_provider(local_chain)

    def snapshot() -> str:
        """Takes a snapshot of the current chain state.

        Returns
        -------
        str
            The snapshot id
        """
        response = _w3.provider.make_request(method=RPCEndpoint("evm_snapshot"), params=[])
        if "result" not in response:
            raise KeyError("Response did not have a result.")
        return response["result"]

    def reset(snapshot_id: str) -> None:
        """Resets the chain to a previous snapshot.

        Arguments
        ---------
        snapshot_id: str
            The snapshot id to reset to.
        """
        # Loads the previous snapshot
        _ = _w3.provider.make_request(method=RPCEndpoint("evm_revert"), params=[snapshot_id])

    return out, snapshot, reset


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
        hyperdrive_contract: Contract
            web3.py contract instance for the hyperdrive contract
        hyperdrive_factory_contract: Contract
            web3.py contract instance for the hyperdrive factory contract
        base_token_contract: Contract
            web3.py contract instance for the base token contract
    """
    # Lots of local  variables for the tests
    # pylint: disable=too-many-locals
    # Deployer is the pre-funded account on the Delv devnet
    deployer_private_key: str = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    # ABI folder should contain JSON and Bytecode files for the following contracts:
    # ERC20Mintable, MockERC4626, ForwarderFactory, ERC4626HyperdriveDeployer, ERC4626HyperdriveFactory

    # Initial pool variables
    # NOTE: we set the initial liquidity here to be very small to ensure we can do trades to ensure withdrawal shares
    # Hence, for testing normal conditions, we likely need to increase the initial liquidity by adding
    # liquidity as the first trade of the pool.
    initial_liquidity = FixedPoint(1_000)
    initial_variable_rate = FixedPoint("0.05")
    initial_fixed_apr = FixedPoint("0.05")  # 5%
    initial_time_stretch_apr = FixedPoint("0.05")  # 5%

    # Factory initialization parameters
    factory_checkpoint_duration_resolution: int = 60 * 60  # 1 hour
    factory_min_checkpoint_duration: int = 60 * 60  # 1 hour
    factory_max_checkpoint_duration: int = 60 * 60 * 24  # 1 day
    factory_min_position_duration: int = 60 * 60 * 24 * 7  # 7 days
    factory_max_position_duration: int = 60 * 60 * 24 * 365 * 10  # 10 year
    factory_min_fixed_apr: FixedPoint = FixedPoint("0.01")  # 1%
    factory_max_fixed_apr: FixedPoint = FixedPoint("0.5")  # 50%
    factory_min_time_stretch_apr: FixedPoint = FixedPoint("0.01")  # 1%
    factory_max_time_stretch_apr: FixedPoint = FixedPoint("0.5")  # 50%

    factory_min_fees = Fees(
        curve=FixedPoint("0.0001").scaled_value,  # .01%
        flat=FixedPoint("0.0001").scaled_value,  # .01%
        governanceLP=FixedPoint("0.15").scaled_value,  # 15%
        governanceZombie=FixedPoint("0.03").scaled_value,  # 3%
    )
    factory_max_fees = Fees(
        curve=FixedPoint("0.1").scaled_value,  # 10%
        flat=FixedPoint("0.001").scaled_value,  # .1%
        governanceLP=FixedPoint("0.15").scaled_value,  # 15%
        governanceZombie=FixedPoint("0.03").scaled_value,  # 3%
    )

    # Deploy Pool initialization parameters
    minimum_share_reserves = FixedPoint(10)
    minimum_transaction_amount = FixedPoint("0.001")
    # TODO the above parameters results in negative interest with the default position duration
    # Hence, we adjust the position duration to be a year to avoid the pool's reserve being 1:1
    # This likely should get fixed by adjusting the time_stretch parameter
    position_duration = 60 * 60 * 24 * 365  # 1 year
    checkpoint_duration = 3600  # 1 hour
    fees = Fees(
        curve=FixedPoint("0.01").scaled_value,  # 1%
        flat=FixedPoint("0.0005").scaled_value,  # 0.05% APR
        governanceLP=FixedPoint("0.15").scaled_value,  # 15%
        governanceZombie=FixedPoint("0.03").scaled_value,  # 3%
    )

    factory_deploy_config = FactoryConfig(
        governance="",  # will be determined in the deploy function
        hyperdriveGovernance="",  # will be determined in the deploy function
        defaultPausers=[],  # We don't support pausers when we deploy
        feeCollector="",  # will be determined in the deploy function
        sweepCollector="",  # will be determined in the deploy function
        checkpointDurationResolution=factory_checkpoint_duration_resolution,
        minCheckpointDuration=factory_min_checkpoint_duration,
        maxCheckpointDuration=factory_max_checkpoint_duration,
        minPositionDuration=factory_min_position_duration,
        maxPositionDuration=factory_max_position_duration,
        minFixedAPR=factory_min_fixed_apr.scaled_value,
        maxFixedAPR=factory_max_fixed_apr.scaled_value,
        minTimeStretchAPR=factory_min_time_stretch_apr.scaled_value,
        maxTimeStretchAPR=factory_max_time_stretch_apr.scaled_value,
        minFees=factory_min_fees,  # pylint: disable=protected-access
        maxFees=factory_max_fees,  # pylint: disable=protected-access
        linkerFactory="",  # will be determined in the deploy function
        linkerCodeHash=bytes(),  # will be determined in the deploy function
    )

    pool_deploy_config = PoolDeployConfig(
        baseToken="",  # will be determined in the deploy function
        linkerFactory="",  # will be determined in the deploy function
        linkerCodeHash=bytes(),  # will be determined in the deploy function
        minimumShareReserves=minimum_share_reserves.scaled_value,
        minimumTransactionAmount=minimum_transaction_amount.scaled_value,
        positionDuration=position_duration,
        checkpointDuration=checkpoint_duration,
        timeStretch=0,
        governance="",  # will be determined in the deploy function
        feeCollector="",  # will be determined in the deploy function
        sweepCollector="",  # will be determined in the deploy function
        fees=fees,
    )
    return deploy_hyperdrive_from_factory(
        local_chain_uri,
        deployer_private_key,
        initial_liquidity,
        initial_variable_rate,
        initial_fixed_apr,
        initial_time_stretch_apr,
        factory_deploy_config,
        pool_deploy_config,
    )


@pytest.fixture(scope="function")
def local_hyperdrive_pool(
    init_local_hyperdrive_pool: tuple[DeployedHyperdrivePool, Callable[[], str], Callable[[str], None]]
) -> Iterator[DeployedHyperdrivePool]:
    """Fixture representing a deployed local hyperdrive pool.

    Arguments
    ---------
    init_local_hyperdrive_pool: tuple[DeployedHyperdrivePool, Callable[[], str], Callable[[str], None]
        Fixture representing the deployed hyperdrive pool, a snapshot function, and a reset function

    Yields
    -------
    DeployedHyperdrivePool
        The various parameters for a deployed pool
    """
    # pylint: disable=redefined-outer-name
    pool, snapshot, reset = init_local_hyperdrive_pool

    # Take snapshot
    snapshot_id = snapshot()

    yield pool

    # Revert to snapshot
    reset(snapshot_id)
