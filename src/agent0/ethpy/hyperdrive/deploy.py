"""Helper functions for deploying Hyperdrive contracts."""

from __future__ import annotations

from enum import Enum
from typing import NamedTuple

from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from fixedpointmath import FixedPoint
from hyperdrivetypes.types import (
    ERC20ForwarderFactoryContract,
    ERC20MintableContract,
    ERC4626HyperdriveCoreDeployerContract,
    ERC4626HyperdriveDeployerCoordinatorContract,
    ERC4626Target0DeployerContract,
    ERC4626Target1DeployerContract,
    ERC4626Target2DeployerContract,
    ERC4626Target3DeployerContract,
    ERC4626Target4DeployerContract,
    HyperdriveFactoryContract,
    IHyperdriveContract,
    LPMathContract,
    MockERC4626Contract,
    MockLidoContract,
    StETHHyperdriveCoreDeployerContract,
    StETHHyperdriveDeployerCoordinatorContract,
    StETHTarget0DeployerContract,
    StETHTarget1DeployerContract,
    StETHTarget2DeployerContract,
    StETHTarget3DeployerContract,
    StETHTarget4DeployerContract,
)
from hyperdrivetypes.types.HyperdriveFactory import FactoryConfig
from hyperdrivetypes.types.IHyperdrive import Options, PoolDeployConfig
from web3 import Web3
from web3.constants import ADDRESS_ZERO
from web3.contract.contract import Contract
from web3.logs import DISCARD
from web3.types import TxParams, Wei

from agent0.ethpy.base import ETH_CONTRACT_ADDRESS, get_account_balance, set_account_balance

# Deploying a Hyperdrive pool requires a long sequence of contract and RPCs,
# resulting in long functions with many parameter arguments.
# pylint: disable=too-many-arguments
# pylint: disable=too-many-positional-arguments
# pylint: disable=too-many-locals

UINT256_MAX = int(2**256 - 1)


class DeployedBaseAndVault(NamedTuple):
    """Collection of attributes associated with a locally deployed Hyperdrive factory."""

    deployer_account: LocalAccount
    base_token_contract: ERC20MintableContract | Contract
    vault_shares_token_contract: MockERC4626Contract | MockLidoContract


class DeployedHyperdriveFactory(NamedTuple):
    """Collection of attributes associated with a locally deployed Hyperdrive factory."""

    deployer_account: LocalAccount
    factory_contract: HyperdriveFactoryContract
    deployer_coordinator_contract: (
        ERC4626HyperdriveDeployerCoordinatorContract | StETHHyperdriveDeployerCoordinatorContract
    )
    factory_deploy_config: FactoryConfig


class DeployedHyperdrivePool(NamedTuple):
    """Collection of attributes associated with a locally deployed chain with a Hyperdrive pool."""

    deployer_account: LocalAccount
    hyperdrive_contract: IHyperdriveContract
    # Keeping the base and vault shares contract generic
    base_token_contract: ERC20MintableContract | Contract
    vault_shares_token_contract: MockERC4626Contract | MockLidoContract
    deploy_block_number: int
    pool_deploy_config: PoolDeployConfig


class HyperdriveDeployType(Enum):
    """The deploy type for the hyperdrive pool."""

    ERC4626 = 0
    STETH = 1


def deploy_base_and_vault(
    web3: Web3,
    deploy_type: HyperdriveDeployType,
    deploy_account: LocalAccount,
    initial_variable_rate: FixedPoint,
) -> DeployedBaseAndVault:
    """Deploys the underlying base and vault contracts

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    deploy_type: HyperdriveDeployType
        The deploy type for the hyperdrive pool.
    deploy_account: LocalAccount
        The account that's deploying the contract.
    initial_variable_rate: FixedPoint
        The starting variable rate for an underlying vault.

    Returns
    -------
    DeployedBaseAndVault
        Containing the deployed base and vault contracts.
    """
    deploy_account_addr = Web3.to_checksum_address(deploy_account.address)

    match deploy_type:
        case HyperdriveDeployType.ERC4626:
            # Deploy base contract
            base_token_contract = ERC20MintableContract.deploy(
                w3=web3,
                account=deploy_account_addr,
                constructor_args=ERC20MintableContract.ConstructorArgs(
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
                constructor_args=MockERC4626Contract.ConstructorArgs(
                    asset=base_token_contract.address,
                    name="Delvnet ERC4626 Yield Source",
                    symbol="ERC4626",
                    initialRate=initial_variable_rate.scaled_value,
                    admin=ADDRESS_ZERO,
                    isCompetitionMode=False,
                    maxMintAmount=UINT256_MAX,
                ),
            )

        case HyperdriveDeployType.STETH:
            # No need to deploy eth contract
            base_token_contract = web3.eth.contract(address=Web3.to_checksum_address(ETH_CONTRACT_ADDRESS))
            vault_contract = MockLidoContract.deploy(
                w3=web3,
                account=deploy_account_addr,
                constructor_args=MockLidoContract.ConstructorArgs(
                    initialRate=initial_variable_rate.scaled_value,
                    admin=ADDRESS_ZERO,
                    isCompetitionMode=False,
                    maxMintAmount=UINT256_MAX,
                ),
            )
            # We fund lido with 1 eth to start to avoid reverts when we
            # initialize the pool
            _ = vault_contract.functions.submit(ADDRESS_ZERO).sign_transact_and_wait(
                deploy_account, TxParams({"value": Wei(FixedPoint(1).scaled_value)}), validate_transaction=True
            )

    return DeployedBaseAndVault(
        deployer_account=deploy_account,
        base_token_contract=base_token_contract,
        vault_shares_token_contract=vault_contract,
    )


def deploy_hyperdrive_factory(
    web3: Web3,
    deployer_account: LocalAccount,
    deployed_base_and_vault: DeployedBaseAndVault,
    deploy_type: HyperdriveDeployType,
    factory_deploy_config: FactoryConfig,
) -> DeployedHyperdriveFactory:
    """Deploys the hyperdrive factory and supporting contracts on the rpc_uri chain.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    deployer_account: LocalAccount
        The account that's deploying the contract.
    deployed_base_and_vault: DeployedBaseAndVault
        The base and vault contracts that were deployed on the local chain.
    deploy_type: HyperdriveDeployType
        The deploy type for the hyperdrive pool.
    factory_deploy_config: FactoryConfig
        The factory configuration for initializing the hyperdrive factory.
        The type is generated from the Hyperdrive ABI using Pypechain.

    Returns
    -------
    DeployedHyperdriveFactory
        Containing the deployed factory, the deploy coordinator contracts, the updated
        factory config, and the hyperdrive registry contract.
    """
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
        deployed_base_and_vault,
        deploy_type,
        factory_deploy_config,
    )


def deploy_hyperdrive_from_factory(
    web3: Web3,
    deployer_account: LocalAccount,
    deployed_base_and_vault: DeployedBaseAndVault,
    deployed_factory: DeployedHyperdriveFactory,
    deploy_type: HyperdriveDeployType,
    initial_liquidity: FixedPoint,
    initial_fixed_apr: FixedPoint,
    initial_time_stretch_apr: FixedPoint,
    pool_deploy_config: PoolDeployConfig,
) -> DeployedHyperdrivePool:
    """Initializes a Hyperdrive pool and supporting contracts on an existing chain.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    deployer_account: LocalAccount
        The local account deploying Hyperdrive.
    deployed_base_and_vault: DeployedBaseAndVault
        The base and vault contracts that were deployed on the local chain.
    deployed_factory: DeployedHyperdriveFactory
        The factory and supporting contracts that were deployed on the local chain.
    deploy_type: HyperdriveDeployType
        The deploy type for the hyperdrive pool.
    initial_liquidity: FixedPoint
        The amount of money to be provided by the `deployer_account` for initial pool liquidity.
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
    deploy_account_addr = Web3.to_checksum_address(deployer_account.address)

    base_token_contract = deployed_base_and_vault.base_token_contract
    vault_contract = deployed_base_and_vault.vault_shares_token_contract

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
            deployed_factory.deployer_coordinator_contract.address,
            deploy_type,
            deployer_account,
            initial_liquidity,
            initial_fixed_apr,
            initial_time_stretch_apr,
            pool_deploy_config,
            deployed_factory.factory_contract,
        )
    )

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


def _deploy_erc4626_deployer(
    web3: Web3,
    deploy_account_addr: ChecksumAddress,
    factory_contract_address: ChecksumAddress,
    lp_math_contract: LPMathContract,
) -> ERC4626HyperdriveDeployerCoordinatorContract:
    core_deployer_contract = ERC4626HyperdriveCoreDeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target0_contract = ERC4626Target0DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        link_references=ERC4626Target0DeployerContract.LinkReferences(LPMath=lp_math_contract),
    )
    target1_contract = ERC4626Target1DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        link_references=ERC4626Target1DeployerContract.LinkReferences(LPMath=lp_math_contract),
    )
    target2_contract = ERC4626Target2DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        link_references=ERC4626Target2DeployerContract.LinkReferences(LPMath=lp_math_contract),
    )
    target3_contract = ERC4626Target3DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        link_references=ERC4626Target3DeployerContract.LinkReferences(LPMath=lp_math_contract),
    )
    target4_contract = ERC4626Target4DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        link_references=ERC4626Target4DeployerContract.LinkReferences(LPMath=lp_math_contract),
    )
    return ERC4626HyperdriveDeployerCoordinatorContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructor_args=ERC4626HyperdriveDeployerCoordinatorContract.ConstructorArgs(
            name="ERC4626HyperdriveDeployerCoordinator",
            factory=factory_contract_address,
            coreDeployer=core_deployer_contract.address,
            target0Deployer=target0_contract.address,
            target1Deployer=target1_contract.address,
            target2Deployer=target2_contract.address,
            target3Deployer=target3_contract.address,
            target4Deployer=target4_contract.address,
        ),
    )


def _deploy_steth_deployer(
    web3: Web3,
    deploy_account_addr: ChecksumAddress,
    factory_contract_address: ChecksumAddress,
    lido_address: ChecksumAddress,
    lp_math_contract: LPMathContract,
) -> StETHHyperdriveDeployerCoordinatorContract:
    core_deployer_contract = StETHHyperdriveCoreDeployerContract.deploy(w3=web3, account=deploy_account_addr)
    target0_contract = StETHTarget0DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        link_references=StETHTarget0DeployerContract.LinkReferences(LPMath=lp_math_contract),
    )
    target1_contract = StETHTarget1DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        link_references=StETHTarget1DeployerContract.LinkReferences(LPMath=lp_math_contract),
    )
    target2_contract = StETHTarget2DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        link_references=StETHTarget2DeployerContract.LinkReferences(LPMath=lp_math_contract),
    )
    target3_contract = StETHTarget3DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        link_references=StETHTarget3DeployerContract.LinkReferences(LPMath=lp_math_contract),
    )
    target4_contract = StETHTarget4DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        link_references=StETHTarget4DeployerContract.LinkReferences(LPMath=lp_math_contract),
    )
    return StETHHyperdriveDeployerCoordinatorContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructor_args=StETHHyperdriveDeployerCoordinatorContract.ConstructorArgs(
            name="StETHHyperdriveDeployerCoordinator",
            factory=factory_contract_address,
            coreDeployer=core_deployer_contract.address,
            target0Deployer=target0_contract.address,
            target1Deployer=target1_contract.address,
            target2Deployer=target2_contract.address,
            target3Deployer=target3_contract.address,
            target4Deployer=target4_contract.address,
            lido=lido_address,
        ),
    )


def _deploy_hyperdrive_factory(
    web3: Web3,
    deployer_account: LocalAccount,
    deployed_base_and_vault: DeployedBaseAndVault,
    deploy_type: HyperdriveDeployType,
    factory_deploy_config: FactoryConfig,
) -> DeployedHyperdriveFactory:
    """Deploys the hyperdrive factory contract on the rpc_uri chain.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    deployer_account: LocalAccount
        The account that's deploying the contract.
    deploy_type: HyperdriveDeployType
        The deploy type for the hyperdrive pool.
    factory_deploy_config: FactoryConfig
        The factory configuration for initializing the hyperdrive factory.
        The type is generated from the Hyperdrive ABI using Pypechain.

    Returns
    -------
    DeloyedHyperdriveFactory
        Contains information on the deployed hyperdrive factory
    """
    deploy_account_addr = Web3.to_checksum_address(deployer_account.address)
    # Deploy forwarder factory
    forwarder_factory_contract = ERC20ForwarderFactoryContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructor_args=ERC20ForwarderFactoryContract.ConstructorArgs(name="ERC20ForwarderFactory"),
    )
    # Set config from forwarder factory contract here
    factory_deploy_config.linkerFactory = forwarder_factory_contract.address
    factory_deploy_config.linkerCodeHash = forwarder_factory_contract.functions.ERC20LINK_HASH().call()
    # Deploy hyperdrive factory
    factory_contract = HyperdriveFactoryContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructor_args=HyperdriveFactoryContract.ConstructorArgs(factory_deploy_config, "HyperdriveFactory"),
    )

    lp_math_contract = LPMathContract.deploy(w3=web3, account=deploy_account_addr)

    match deploy_type:
        case HyperdriveDeployType.ERC4626:
            deployer_coordinator_contract = _deploy_erc4626_deployer(
                web3,
                deploy_account_addr,
                factory_contract.address,
                lp_math_contract,
            )
        case HyperdriveDeployType.STETH:
            deployer_coordinator_contract = _deploy_steth_deployer(
                web3,
                deploy_account_addr,
                factory_contract.address,
                deployed_base_and_vault.vault_shares_token_contract.address,
                lp_math_contract,
            )

    _ = factory_contract.functions.addDeployerCoordinator(deployer_coordinator_contract.address).sign_transact_and_wait(
        deployer_account, validate_transaction=True
    )

    return DeployedHyperdriveFactory(
        deployer_account=deployer_account,
        factory_contract=factory_contract,
        deployer_coordinator_contract=deployer_coordinator_contract,
        factory_deploy_config=factory_deploy_config,
    )


def _mint_and_approve(
    web3,
    funding_account: LocalAccount,
    funding_contract: ERC20MintableContract | Contract,
    contract_to_approve: Contract,
    mint_amount: FixedPoint,
) -> None:
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

    """
    if funding_contract.address == ETH_CONTRACT_ADDRESS:
        # No need to approve, but we still need to ensure there's enough eth to fund
        eth_balance = FixedPoint(scaled_value=get_account_balance(web3, funding_account.address))
        new_eth_balance = eth_balance + mint_amount
        _ = set_account_balance(web3, funding_account.address, new_eth_balance.scaled_value)

    else:
        assert isinstance(funding_contract, ERC20MintableContract)
        _ = funding_contract.functions.mint(funding_account.address, mint_amount.scaled_value).sign_transact_and_wait(
            funding_account, validate_transaction=True
        )

        _ = funding_contract.functions.approve(
            contract_to_approve.address, mint_amount.scaled_value
        ).sign_transact_and_wait(funding_account, validate_transaction=True)


def _deploy_and_initialize_hyperdrive_pool(
    deployer_coordinator_address: ChecksumAddress,
    deploy_type: HyperdriveDeployType,
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
    for target_index in range(5):
        _ = factory_contract.functions.deployTarget(
            _deploymentId=deployment_id,
            _deployerCoordinator=deployer_coordinator_address,
            _config=pool_deploy_config,
            _extraData=bytes(0),  # Vec::new().info()
            _fixedAPR=initial_fixed_apr.scaled_value,
            _timeStretchAPR=initial_time_stretch_apr.scaled_value,
            _targetIndex=target_index,
            _salt=salt,
        ).sign_transact_and_wait(deploy_account, validate_transaction=True)

    match deploy_type:
        case HyperdriveDeployType.ERC4626:
            name = "agent0_erc4626"
            txn_option_value = None
        case HyperdriveDeployType.STETH:
            name = "agent0_steth"
            # Transaction to `deployAndInitialize` needs value field since it's transfering eth
            txn_option_value = initial_liquidity.scaled_value

    tx_args = TxParams()
    if txn_option_value is not None:
        tx_args["value"] = Wei(txn_option_value)
    tx_receipt = factory_contract.functions.deployAndInitialize(
        __name=name,
        _deploymentId=deployment_id,
        _deployerCoordinator=deployer_coordinator_address,
        _config=pool_deploy_config,
        _extraData=bytes(0),
        _contribution=initial_liquidity.scaled_value,
        _fixedAPR=initial_fixed_apr.scaled_value,
        _timeStretchAPR=initial_time_stretch_apr.scaled_value,
        _options=Options(
            asBase=True,
            destination=Web3.to_checksum_address(deploy_account.address),
            extraData=bytes(0),
        ),
        _salt=salt,
    ).sign_transact_and_wait(deploy_account, tx_args, validate_transaction=True)

    deploy_events = list(factory_contract.events.Deployed.process_receipt_typed(tx_receipt, errors=DISCARD))
    if len(deploy_events) != 1:
        raise AssertionError(f"Expected 1 Deployed event, got {len(deploy_events)}")
    hyperdrive_address = deploy_events[0].args.hyperdrive
    return hyperdrive_address
