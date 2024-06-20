"""Helper functions for deploying Hyperdrive contracts."""

from __future__ import annotations

from typing import NamedTuple

from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
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
    FactoryConfig,
    HyperdriveFactoryContract,
    HyperdriveRegistryContract,
    IHyperdriveContract,
    LPMathContract,
    MockERC4626Contract,
    Options,
    PoolDeployConfig,
)
from agent0.hypertypes.types.ERC4626Target0DeployerContract import erc4626target0deployer_bytecode
from agent0.hypertypes.types.ERC4626Target1DeployerContract import erc4626target1deployer_bytecode
from agent0.hypertypes.types.ERC4626Target2DeployerContract import erc4626target2deployer_bytecode
from agent0.hypertypes.types.ERC4626Target3DeployerContract import erc4626target3deployer_bytecode

# Deploying a Hyperdrive pool requires a long sequence of contract and RPCs,
# resulting in long functions with many parameter arguments.
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals

UINT256_MAX = int(2**256 - 1)


class DeployedHyperdriveFactory(NamedTuple):
    """Collection of attributes associated with a locally deployed Hyperdrive factory."""

    deployer_account: LocalAccount
    factory_contract: HyperdriveFactoryContract
    deployer_coordinator_contract: ERC4626HyperdriveDeployerCoordinatorContract
    registry_contract: HyperdriveRegistryContract
    factory_deploy_config: FactoryConfig


class DeployedHyperdrivePool(NamedTuple):
    """Collection of attributes associated with a locally deployed chain with a Hyperdrive pool."""

    deployer_account: LocalAccount
    hyperdrive_contract: IHyperdriveContract
    # Keeping the base and vault shares contract generic
    base_token_contract: Contract
    vault_shares_token_contract: Contract
    deploy_block_number: int
    pool_deploy_config: PoolDeployConfig


def deploy_hyperdrive_factory(
    rpc_uri: str,
    deployer_account: LocalAccount,
    factory_deploy_config: FactoryConfig,
) -> DeployedHyperdriveFactory:
    """Deploys the hyperdrive factory and supporting contracts on the rpc_uri chain.

    Arguments
    ---------
    rpc_uri: str
        The URI of the RPC node.
    deployer_account: LocalAccount
        The account that's deploying the contract.
    factory_deploy_config: FactoryConfig
        The factory configuration for initializing the hyperdrive factory.
        The type is generated from the Hyperdrive ABI using Pypechain.

    Returns
    -------
    DeployedHyperdriveFactory
        Containing the deployed factory, the deploy coordinator contracts, the updated
        factory config, and the hyperdrive registry contract.
    """
    # Contract calls use the web3.py interface
    web3 = initialize_web3_with_http_provider(rpc_uri, reset_provider=False)
    # Create the pre-funded account on the Delv devnet
    deploy_account_addr = Web3.to_checksum_address(deployer_account.address)

    # Update various configs with the deploy account address
    factory_deploy_config.governance = deploy_account_addr
    factory_deploy_config.deployerCoordinatorManager = deploy_account_addr
    factory_deploy_config.hyperdriveGovernance = deploy_account_addr
    factory_deploy_config.feeCollector = deploy_account_addr
    factory_deploy_config.sweepCollector = deploy_account_addr
    factory_deploy_config.checkpointRewarder = ADDRESS_ZERO

    # Deploy the factory and base token contracts
    return _deploy_hyperdrive_factory(
        web3,
        deployer_account,
        factory_deploy_config,
    )


def deploy_hyperdrive_from_factory(
    rpc_uri: str,
    deployer_account: LocalAccount,
    deployed_factory: DeployedHyperdriveFactory,
    initial_liquidity: FixedPoint,
    initial_variable_rate: FixedPoint,
    initial_fixed_apr: FixedPoint,
    initial_time_stretch_apr: FixedPoint,
    pool_deploy_config: PoolDeployConfig,
) -> DeployedHyperdrivePool:
    """Initializes a Hyperdrive pool and supporting contracts on an existing chain.

    Arguments
    ---------
    rpc_uri: str
        The URI of the local RPC node.
    deployer_account: LocalAccount
        The local account deploying Hyperdrive.
    deployed_factory: DeployedHyperdriveFactory
        The factory and supporting contracts that were deployed on the local chain.
    initial_liquidity: FixedPoint
        The amount of money to be provided by the `deployer_account` for initial pool liquidity.
    initial_variable_rate: FixedPoint
        The starting variable rate for an underlying vault.
    initial_fixed_apr: FixedPoint
        The fixed rate of the pool on initialization.
    initial_time_stretch_apr: FixedPoint
        The apr to target for the time stretch calculation.
    pool_deploy_config: PoolDeployConfig
        The configuration for initializing hyperdrive pool.
        The type is generated from the Hyperdrive ABI using Pypechain.

    Returns
    -------
    DeployedHyperdrivePool
        A named tuple with the following fields:
            deploy_account: LocalAccount
                The local account that deploys and initializes hyperdrive.
            hyperdrive_contract: IHyperdriveContract
                Web3 contract instance for the hyperdrive contract.
            base_token_contract: Contract
                Web3 contract instance for the base token contract.
            vault_shares_token_contract: Contract
                Web3 contract instance for the vault shares token contract.
            deploy_block_number: int
                The block number hyperdrive was deployed at.
    """

    # Contract calls use the web3.py interface
    web3 = initialize_web3_with_http_provider(rpc_uri, reset_provider=False)

    # Create the pre-funded account on the Delv devnet
    deploy_account_addr = Web3.to_checksum_address(deployer_account.address)

    base_token_contract, vault_contract = _deploy_base_and_vault(web3, deployer_account, initial_variable_rate)

    # Update pool deploy config with factory settings
    pool_deploy_config.baseToken = base_token_contract.address
    pool_deploy_config.vaultSharesToken = vault_contract.address
    pool_deploy_config.governance = deploy_account_addr
    pool_deploy_config.feeCollector = deploy_account_addr
    pool_deploy_config.sweepCollector = deploy_account_addr
    pool_deploy_config.linkerFactory = deployed_factory.factory_deploy_config.linkerFactory
    pool_deploy_config.linkerCodeHash = deployed_factory.factory_deploy_config.linkerCodeHash
    pool_deploy_config.checkpointRewarder = deployed_factory.factory_deploy_config.checkpointRewarder

    # Mint base and approve the initial liquidity amount for the hyperdrive factory
    _mint_and_approve(
        web3=web3,
        funding_account=deployer_account,
        funding_contract=base_token_contract,
        contract_to_approve=deployed_factory.deployer_coordinator_contract,
        mint_amount=initial_liquidity,
    )

    # Deploy the Hyperdrive contract and call the initialize function
    hyperdrive_checksum_address = Web3.to_checksum_address(
        _deploy_and_initialize_hyperdrive_pool(
            web3,
            deployed_factory.deployer_coordinator_contract.address,
            deployer_account,
            initial_liquidity,
            initial_fixed_apr,
            initial_time_stretch_apr,
            pool_deploy_config,
            deployed_factory.factory_contract,
        )
    )

    # Register this pool with the registry contract
    register_function = deployed_factory.registry_contract.functions.setInstanceInfo(
        [hyperdrive_checksum_address], [1], [deployed_factory.factory_contract.address]
    )
    function_name = register_function.fn_name
    function_args = register_function.args
    receipt = smart_contract_transact(
        web3,
        deployed_factory.registry_contract,
        deployer_account,
        function_name,
        *function_args,
    )
    if receipt["status"] != 1:
        raise ValueError(f"Failed to register Hyperdrive contract.\n{receipt=}")

    # Register the admin account
    register_function = deployed_factory.registry_contract.functions.updateAdmin(deploy_account_addr)
    function_name = register_function.fn_name
    function_args = register_function.args
    receipt = smart_contract_transact(
        web3,
        deployed_factory.registry_contract,
        deployer_account,
        function_name,
        *function_args,
    )
    if receipt["status"] != 1:
        raise ValueError(f"Failed to register Hyperdrive deployer admin address.\n{receipt=}")

    # Get block number when hyperdrive was deployed
    return DeployedHyperdrivePool(
        deployer_account=deployer_account,
        hyperdrive_contract=IHyperdriveContract.factory(web3)(hyperdrive_checksum_address),
        base_token_contract=base_token_contract,
        vault_shares_token_contract=vault_contract,
        deploy_block_number=web3.eth.block_number,
        pool_deploy_config=pool_deploy_config,
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
    deployer_account: LocalAccount,
    factory_deploy_config: FactoryConfig,
) -> DeployedHyperdriveFactory:
    """Deploys the hyperdrive factory contract on the rpc_uri chain.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    deployer_account: LocalAccount
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
    deploy_account_addr = Web3.to_checksum_address(deployer_account.address)
    # Deploy forwarder factory
    forwarder_factory_contract = ERC20ForwarderFactoryContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructorArgs=ERC20ForwarderFactoryContract.ConstructorArgs(name="ERC20ForwarderFactory"),
    )
    # Set config from forwarder factory contract here
    factory_deploy_config.linkerFactory = forwarder_factory_contract.address
    factory_deploy_config.linkerCodeHash = forwarder_factory_contract.functions.ERC20LINK_HASH().call()
    # Deploy hyperdrive factory
    factory_contract = HyperdriveFactoryContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructorArgs=HyperdriveFactoryContract.ConstructorArgs(factory_deploy_config, "HyperdriveFactory"),
    )

    lp_math_contract = LPMathContract.deploy(w3=web3, account=deploy_account_addr)
    # Deploying the target deployer contracts requires linking to the LPMath contract.
    # We do this by replacing the `linked_str` pattern with address of lp_math_contract.
    # The `linked_str` pattern is the identifier of the LP Math contract for
    # "contracts/src/libraries/LPMath.sol"
    linked_str = "__$2b4fa6f02a36eedfe41c65e8dd342257d3$__"
    linked_contract_addr = lp_math_contract.address[2:].lower()
    ERC4626Target0DeployerContract.bytecode = HexBytes(
        str(erc4626target0deployer_bytecode).replace(linked_str, linked_contract_addr)
    )
    ERC4626Target1DeployerContract.bytecode = HexBytes(
        str(erc4626target1deployer_bytecode).replace(linked_str, linked_contract_addr)
    )
    ERC4626Target2DeployerContract.bytecode = HexBytes(
        str(erc4626target2deployer_bytecode).replace(linked_str, linked_contract_addr)
    )
    ERC4626Target3DeployerContract.bytecode = HexBytes(
        str(erc4626target3deployer_bytecode).replace(linked_str, linked_contract_addr)
    )

    core_deployer_contract = ERC4626HyperdriveCoreDeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target0_contract = ERC4626Target0DeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target1_contract = ERC4626Target1DeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target2_contract = ERC4626Target2DeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target3_contract = ERC4626Target3DeployerContract.deploy(w3=web3, account=deploy_account_addr)
    deployer_coordinator_contract = ERC4626HyperdriveDeployerCoordinatorContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructorArgs=ERC4626HyperdriveDeployerCoordinatorContract.ConstructorArgs(
            name="HyperdriveDeployerCoordinator",
            factory=factory_contract.address,
            coreDeployer=core_deployer_contract.address,
            target0Deployer=target0_contract.address,
            target1Deployer=target1_contract.address,
            target2Deployer=target2_contract.address,
            target3Deployer=target3_contract.address,
        ),
    )
    add_deployer_coordinator_function = factory_contract.functions.addDeployerCoordinator(
        deployer_coordinator_contract.address
    )
    function_name = add_deployer_coordinator_function.fn_name
    function_args = add_deployer_coordinator_function.args
    receipt = smart_contract_transact(
        web3,
        factory_contract,
        deployer_account,
        function_name,
        *function_args,
    )
    if receipt["status"] != 1:
        raise ValueError(f"Failed adding the Hyperdrive deployer to the factory.\n{receipt=}")

    # Deploy the Hyperdrive registry contract
    registry_contract = HyperdriveRegistryContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructorArgs=HyperdriveRegistryContract.ConstructorArgs(name="HyperdriveRegistry"),
    )

    # Register the factory with the registry contract
    register_function = registry_contract.functions.setFactoryInfo([factory_contract.address], [1])
    function_name = register_function.fn_name
    function_args = register_function.args
    receipt = smart_contract_transact(
        web3,
        registry_contract,
        deployer_account,
        function_name,
        *function_args,
    )
    if receipt["status"] != 1:
        raise ValueError(f"Failed to register Hyperdrive factory.\n{receipt=}")

    return DeployedHyperdriveFactory(
        deployer_account=deployer_account,
        factory_contract=factory_contract,
        deployer_coordinator_contract=deployer_coordinator_contract,
        factory_deploy_config=factory_deploy_config,
        registry_contract=registry_contract,
    )


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
            name="Base",
            symbol="BASE",
            decimals=18,
            admin=ADDRESS_ZERO,
            isCompetitionMode_=False,
            maxMintAmount_=UINT256_MAX,
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
            maxMintAmount=UINT256_MAX,
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

    # There are 4 contracts to deploy, we call deployTarget on all of them
    for target_index in range(4):
        deploy_target_function = factory_contract.functions.deployTarget(
            deploymentId=deployment_id,
            deployerCoordinator=deployer_coordinator_address,
            config=pool_deploy_config,
            extraData=bytes(0),  # Vec::new().info()
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
        if receipt["status"] != 1:
            raise ValueError(f"Failed calling deployTarget on target {target_index}.\n{receipt=}")

    deploy_and_init_function = factory_contract.functions.deployAndInitialize(
        name="agent0_erc4626",
        deploymentId=deployment_id,
        deployerCoordinator=deployer_coordinator_address,
        config=pool_deploy_config,
        extraData=bytes(0),
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
