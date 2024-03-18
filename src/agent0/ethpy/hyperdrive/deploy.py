"""Helper functions for deploying Hyperdrive contracts."""

from __future__ import annotations

from typing import NamedTuple

from eth_abi.abi import encode
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.constants import ADDRESS_ZERO
from web3.contract.contract import Contract
from web3.types import TxReceipt

from agent0.ethpy.base import initialize_web3_with_http_provider
from agent0.ethpy.base.receipts import get_transaction_logs
from agent0.ethpy.base.transactions import smart_contract_transact
from agent0.hypertypes import (
    ERC20ForwarderFactoryContract,
    ERC20MintableContract,
    ERC4626HyperdriveCoreDeployerContract,
    ERC4626HyperdriveDeployerCoordinatorContract,
    ERC4626Target0DeployerContract,
    ERC4626Target1DeployerContract,
    ERC4626Target2DeployerContract,
    ERC4626Target3DeployerContract,
    ERC4626Target4DeployerContract,
    FactoryConfig,
    HyperdriveFactoryContract,
    IERC4626HyperdriveContract,
    MockERC4626Contract,
    Options,
    PoolDeployConfig,
)

from .addresses import HyperdriveAddresses

# Deploying a Hyperdrive pool requires a long sequence of contract and RPCs,
# resulting in long functions with many parameter arguments.
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals


class DeployedHyperdrivePool(NamedTuple):
    """Collection of attributes associated with a locally deployed chain with a Hyperdrive pool."""

    web3: Web3
    deploy_account: LocalAccount
    hyperdrive_contract_addresses: HyperdriveAddresses
    hyperdrive_contract: Contract
    hyperdrive_factory_contract: Contract
    base_token_contract: Contract
    deploy_block_number: int


def deploy_hyperdrive_from_factory(
    rpc_uri: str,
    deployer_private_key: str,
    initial_liquidity: FixedPoint,
    initial_variable_rate: FixedPoint,
    initial_fixed_apr: FixedPoint,
    initial_time_stretch_apr: FixedPoint,
    factory_deploy_config: FactoryConfig,
    pool_deploy_config: PoolDeployConfig,
) -> DeployedHyperdrivePool:
    """Initializes a Hyperdrive pool on an existing chain.

    Arguments
    ---------
    rpc_uri: str
        The URI of the local RPC node.
    deployer_private_key: str
        Private key for the funded wallet for deploying Hyperdrive.
    initial_liquidity: FixedPoint
        The amount of money to be provided by the `deploy_account` for initial pool liquidity.
    initial_variable_rate: FixedPoint
        The starting variable rate for an underlying vault.
    initial_fixed_apr: FixedPoint
        The fixed rate of the pool on initialization.
    initial_time_stretch_apr: FixedPoint
        The apr to target for the time stretch calculation.
    factory_deploy_config: FactoryConfig
        The configuration for initializing the hyperdrive factory.
        The type is generated from the Hyperdrive ABI using Pypechain.
    pool_deploy_config: PoolDeployConfig
        The configuration for initializing hyperdrive pool.
        The type is generated from the Hyperdrive ABI using Pypechain.

    Returns
    -------
    LocalHyperdriveChain
        A named tuple with the following fields:
            web3: Web3
                Web3 provider object.
            deploy_account: LocalAccount
                The local account that deploys and initializes hyperdrive.
            hyperdrive_contract_addresses: HyperdriveAddresses
                The hyperdrive contract addresses.
            hyperdrive_contract: Contract
                Web3 contract instance for the hyperdrive contract.
            hyperdrive_factory_contract: Contract
                Web3 contract instance for the hyperdrive factory contract.
            base_token_contract: Contract
                Web3 contract instance for the base token contract.
            deploy_block_number: int
                The block number hyperdrive was deployed at.
    """
    # Contract calls use the web3.py interface
    web3 = initialize_web3_with_http_provider(rpc_uri, reset_provider=False)
    # Create the pre-funded account on the Delv devnet
    deploy_account = _initialize_deployment_account(web3, deployer_private_key)
    deploy_account_addr = Web3.to_checksum_address(deploy_account.address)

    # Update various configs with the deploy account address
    factory_deploy_config.governance = deploy_account_addr
    factory_deploy_config.hyperdriveGovernance = deploy_account_addr
    factory_deploy_config.feeCollector = deploy_account_addr
    factory_deploy_config.sweepCollector = deploy_account_addr

    # Deploy the factory and base token contracts
    factory_contract, deployer_contract, factory_deploy_config = _deploy_hyperdrive_factory(
        web3,
        deploy_account,
        factory_deploy_config,
    )

    base_token_contract, vault_contract = _deploy_base_and_vault(web3, deploy_account, initial_variable_rate)

    # Update pool deploy config with factory settings
    pool_deploy_config.baseToken = base_token_contract.address
    pool_deploy_config.governance = deploy_account_addr
    pool_deploy_config.feeCollector = deploy_account_addr
    pool_deploy_config.sweepCollector = deploy_account_addr
    pool_deploy_config.linkerFactory = factory_deploy_config.linkerFactory
    pool_deploy_config.linkerCodeHash = factory_deploy_config.linkerCodeHash

    # Mint base and approve the initial liquidity amount for the hyperdrive factory
    _mint_and_approve(
        web3=web3,
        funding_account=deploy_account,
        funding_contract=base_token_contract,
        contract_to_approve=deployer_contract,
        mint_amount=initial_liquidity,
    )

    # Deploy the Hyperdrive contract and call the initialize function
    hyperdrive_checksum_address = Web3.to_checksum_address(
        _deploy_and_initialize_hyperdrive_pool(
            web3,
            deployer_contract.address,
            deploy_account,
            initial_liquidity,
            initial_fixed_apr,
            initial_time_stretch_apr,
            vault_contract.address,
            pool_deploy_config,
            factory_contract,
        )
    )
    # Get block number when hyperdrive was deployed
    return DeployedHyperdrivePool(
        web3,
        deploy_account=deploy_account,
        hyperdrive_contract_addresses=HyperdriveAddresses(
            base_token=Web3.to_checksum_address(base_token_contract.address),
            factory=Web3.to_checksum_address(factory_contract.address),
            erc4626_hyperdrive=hyperdrive_checksum_address,
            # We don't deploy a steth hyperdrive here, so we don't set this address
            steth_hyperdrive=Web3.to_checksum_address(ADDRESS_ZERO),
        ),
        hyperdrive_contract=IERC4626HyperdriveContract.factory(web3)(hyperdrive_checksum_address),
        hyperdrive_factory_contract=factory_contract,
        base_token_contract=base_token_contract,
        deploy_block_number=web3.eth.block_number,
    )


def _initialize_deployment_account(web3: Web3, account_private_key: str) -> LocalAccount:
    """Initializes the local anvil account to deploy everything from.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    account_private_key: str
        Private key for the funded wallet for deploying Hyperdrive.

    Returns
    -------
    LocalAccount
        A Web3 LocalAccount for the given private key.

    .. todo::
        get private key for `account_private_key` of this account programmatically
        https://github.com/delvtech/agent0/issues/816
        This is the private key of account 0 of the anvil pre-funded account
    """
    account: LocalAccount = Account().from_key(account_private_key)
    # Ensure this private key is actually matched to the first address of anvil
    assert web3.eth.accounts[0] == account.address
    return account


def _deploy_hyperdrive_factory(
    web3: Web3,
    deploy_account: LocalAccount,
    factory_deploy_config: FactoryConfig,
) -> tuple[HyperdriveFactoryContract, ERC4626HyperdriveDeployerCoordinatorContract, FactoryConfig]:
    """Deploys the hyperdrive factory contract on the rpc_uri chain.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    deploy_account: LocalAccount
        The account that's deploying the contract.
    factory_deploy_config: FactoryConfig
        The factory configuration for initializing the hyperdrive factory.
        The type is generated from the Hyperdrive ABI using Pypechain.

    Returns
    -------
    tuple[
        HyperdriveFactoryContract,
        ERC4626HyperdriveDeployerCoordinatorContract,
        FactoryConfig,
    ]
        Containing the deployed factory, the deploy coordinator contracts, and the updated
        factory config
    """
    deploy_account_addr = Web3.to_checksum_address(deploy_account.address)
    # Deploy forwarder factory
    forwarder_factory_contract = ERC20ForwarderFactoryContract.deploy(w3=web3, account=deploy_account_addr)
    # Set config from forwarder factory contract here
    factory_deploy_config.linkerFactory = forwarder_factory_contract.address
    factory_deploy_config.linkerCodeHash = forwarder_factory_contract.functions.ERC20LINK_HASH().call()
    # Deploy hyperdrive factory
    factory_contract = HyperdriveFactoryContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructorArgs=HyperdriveFactoryContract.ConstructorArgs(factory_deploy_config),
    )
    core_deployer_contract = ERC4626HyperdriveCoreDeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target0_contract = ERC4626Target0DeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target1_contract = ERC4626Target1DeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target2_contract = ERC4626Target2DeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target3_contract = ERC4626Target3DeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target4_contract = ERC4626Target4DeployerContract.deploy(w3=web3, account=deploy_account_addr)
    deployer_contract = ERC4626HyperdriveDeployerCoordinatorContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructorArgs=ERC4626HyperdriveDeployerCoordinatorContract.ConstructorArgs(
            coreDeployer=core_deployer_contract.address,
            target0Deployer=target0_contract.address,
            target1Deployer=target1_contract.address,
            target2Deployer=target2_contract.address,
            target3Deployer=target3_contract.address,
            target4Deployer=target4_contract.address,
        ),
    )
    add_deployer_coordinator_function = factory_contract.functions.addDeployerCoordinator(deployer_contract.address)
    function_name = add_deployer_coordinator_function.fn_name
    function_args = add_deployer_coordinator_function.args
    receipt = smart_contract_transact(
        web3,
        factory_contract,
        deploy_account,
        function_name,
        *function_args,
    )
    assert receipt["status"] == 1, f"Failed adding the Hyperdrive deployer to the factory.\n{receipt=}"
    return factory_contract, deployer_contract, factory_deploy_config


def _deploy_base_and_vault(
    web3: Web3, deploy_account: LocalAccount, initial_variable_rate: FixedPoint
) -> tuple[ERC20MintableContract, MockERC4626Contract]:
    """Deploys the underlying base and vault contracts

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    deploy_account: LocalAccount
        The account that's deploying the contract.
    initial_variable_rate: FixedPoint
        The starting variable rate for an underlying vault.

    Returns
    -------
    tuple[
        ERC20MintableContract,
        MockERC4626Contract,
    ]
        Containing the deployed base and vault contracts.
    """
    deploy_account_addr = Web3.to_checksum_address(deploy_account.address)
    # Deploy base contract
    base_token_contract = ERC20MintableContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructorArgs=ERC20MintableContract.ConstructorArgs(
            name="Base", symbol="BASE", decimals=18, admin=ADDRESS_ZERO, isCompetitionMode_=False
        ),
    )
    # Deploy the vault contract
    vault_contract = MockERC4626Contract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructorArgs=MockERC4626Contract.ConstructorArgs(
            asset=base_token_contract.address,
            name="Delvnet Yield Source",
            symbol="DELV",
            initialRate=initial_variable_rate.scaled_value,
            admin=ADDRESS_ZERO,
            isCompetitionMode=False,
        ),
    )
    return base_token_contract, vault_contract


def _mint_and_approve(
    web3,
    funding_account: LocalAccount,
    funding_contract: ERC20MintableContract,
    contract_to_approve: ERC4626HyperdriveDeployerCoordinatorContract,
    mint_amount: FixedPoint,
) -> tuple[TxReceipt, TxReceipt]:
    """Mint tokens from the funding_contract and approve spending with the contract_to_approve

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    funding_account: LocalAccount
        A Web3 LocalAccount for the given private key.
    funding_contract: Contract
        Web3 contract instance for the contract used to mint tokens.
    contract_to_approve: Contract
        Web3 contract instance for the contract that needs approval from the funding contract.
    mint_amount: FixedPoint
        The amount to mint and approve.

    Returns
    -------
    tuple[TxReceipt, TxReceipt]
        The (mint, approval) transaction receipts.

    """
    # Need to pass signature instead of function name since there are multiple mint functions
    mint_tx_receipt = smart_contract_transact(
        web3,
        funding_contract,
        funding_account,
        "mint(address,uint256)",
        Web3.to_checksum_address(funding_account.address),
        mint_amount.scaled_value,
    )
    approve_tx_receipt = smart_contract_transact(
        web3,
        funding_contract,
        funding_account,
        "approve",
        contract_to_approve.address,
        mint_amount.scaled_value,
    )
    return mint_tx_receipt, approve_tx_receipt


def _deploy_and_initialize_hyperdrive_pool(
    web3: Web3,
    deployer_coordinator_address: ChecksumAddress,
    deploy_account: LocalAccount,
    initial_liquidity: FixedPoint,
    initial_fixed_apr: FixedPoint,
    initial_time_stretch_apr: FixedPoint,
    vault_contract_addr: ChecksumAddress,
    pool_deploy_config: PoolDeployConfig,
    factory_contract: HyperdriveFactoryContract,
) -> str:
    """Deploys the hyperdrive factory contract on the rpc_uri chain.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    deployer_coordinator_address: ChecksumAddress
        The address for the deployed ERC4626HyperdriveDeployer contract.
    deploy_account: LocalAccount
        A Web3 LocalAccount for the given private key.
    initial_liquidity: FixedPoint
        The amount of money to be provided by the `deploy_account` for initial pool liquidity.
    initial_fixed_apr: FixedPoint
        The fixed rate of the pool on initialization.
    initial_time_stretch_apr: FixedPoint
        The apr to target for the time stretch.
    vault_contract_addr: ChecksumAddress
        The address of the vault contract.
    pool_deploy_config: PoolDeployConfig
        The configuration for initializing hyperdrive.
        The type is generated from the Hyperdrive ABI using Pypechain.
    factory_contract: HyperdriveFactoryContract
        The hyperdrive factory contract.

    Returns
    -------
    str
        The deployed hyperdrive contract address.
    """
    # We hard code the deployment ID and salt here
    # These will conflict if we deploy multiple pools using one factory,
    # but we have a one-to-one relationship between factory and pools in simulation
    # so hard coding these should be okay
    # Web3 requires exactly 32 bytes for these parameters, hence, we create a 28 byte zero array,
    # concatenated with a hard coded 4 byte hex
    deployment_id = bytes(28) + bytes.fromhex("deadbeef")
    salt = bytes(28) + bytes.fromhex("deadbabe")

    min_checkpoint_duration = factory_contract.functions.minCheckpointDuration().call()
    max_checkpoint_duration = factory_contract.functions.maxCheckpointDuration().call()
    if (
        pool_deploy_config.checkpointDuration < min_checkpoint_duration
        or pool_deploy_config.checkpointDuration > max_checkpoint_duration
    ):
        raise ValueError(
            f"{pool_deploy_config.checkpointDuration=} must be between "
            f"{min_checkpoint_duration=} and {max_checkpoint_duration=}"
        )

    # There are 5 contracts to deploy, we call deployTarget on all of them
    for target_index in range(5):
        deploy_target_function = factory_contract.functions.deployTarget(
            deploymentId=deployment_id,
            deployerCoordinator=deployer_coordinator_address,
            config=pool_deploy_config,
            extraData=encode(("address",), (vault_contract_addr,)),
            fixedAPR=initial_fixed_apr.scaled_value,
            timeStretchAPR=initial_time_stretch_apr.scaled_value,
            targetIndex=target_index,
            salt=salt,
        )
        function_name = deploy_target_function.fn_name
        function_args = deploy_target_function.args
        receipt = smart_contract_transact(
            web3,
            factory_contract,
            deploy_account,
            function_name,
            *function_args,
        )
        assert receipt["status"] == 1, f"Failed calling deployTarget on target {target_index}.\n{receipt=}"

    deploy_and_init_function = factory_contract.functions.deployAndInitialize(
        deploymentId=deployment_id,
        deployerCoordinator=deployer_coordinator_address,
        config=pool_deploy_config,
        extraData=encode(("address",), (vault_contract_addr,)),
        contribution=initial_liquidity.scaled_value,
        fixedAPR=initial_fixed_apr.scaled_value,
        timeStretchAPR=initial_time_stretch_apr.scaled_value,
        options=Options(
            asBase=True,
            destination=Web3.to_checksum_address(deploy_account.address),
            extraData=bytes(0),
        ),
        salt=salt,
    )

    function_name = deploy_and_init_function.fn_name
    function_args = deploy_and_init_function.args
    tx_receipt = smart_contract_transact(
        web3,
        factory_contract,
        deploy_account,
        function_name,
        *function_args,
    )
    logs = get_transaction_logs(factory_contract, tx_receipt)
    hyperdrive_address: str | None = None
    for log in logs:
        if log["event"] == "GovernanceUpdated":
            hyperdrive_address = log["address"]
    if hyperdrive_address is None:
        raise AssertionError("Generating hyperdrive contract didn't return address")
    return hyperdrive_address
