"""Helper functions for deploying Hyperdrive contracts."""
from __future__ import annotations

from typing import NamedTuple

from eth_abi import encode
from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from ethpy.base import initialize_web3_with_http_provider
from ethpy.base.receipts import get_transaction_logs
from ethpy.base.transactions import smart_contract_transact
from fixedpointmath import FixedPoint
from hypertypes import Fees, PoolConfig
from hypertypes.types import (
    ERC20MintableContract,
    ERC4626HyperdriveCoreDeployerContract,
    ERC4626HyperdriveDeployerContract,
    ERC4626HyperdriveFactoryContract,
    ERC4626Target0DeployerContract,
    ERC4626Target1DeployerContract,
    ForwarderFactoryContract,
    IERC4626HyperdriveContract,
    MockERC4626Contract,
)
from hypertypes.types.ERC4626HyperdriveFactoryTypes import FactoryConfig
from web3 import Web3
from web3.constants import ADDRESS_ZERO
from web3.contract.contract import Contract
from web3.types import TxReceipt

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
    initial_fixed_rate: FixedPoint,
    pool_config: PoolConfig,
    max_fees: Fees,
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
        The starting variable rate for an underlying yield source.
    initial_fixed_rate: FixedPoint
        The fixed rate of the pool on initialization.
    pool_config: PoolConfig
        The configuration for initializing hyperdrive.
        The type is generated from the Hyperdrive ABI using Pypechain.
    max_fees: Fees
        The maximum value for the setup fees.

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
    # Fill in the pool config information for the deployer account address
    pool_config.governance = deploy_account_addr
    pool_config.feeCollector = deploy_account_addr
    # Deploy the factory and base token contracts
    base_token_contract, factory_contract, pool_contract_addr, deployer_contract_addr = _deploy_hyperdrive_factory(
        web3,
        deploy_account_addr,
        initial_variable_rate,
        pool_config,
        max_fees,
    )
    receipt = smart_contract_transact(
        web3, factory_contract, deploy_account, "addHyperdriveDeployer", deployer_contract_addr
    )
    assert receipt["status"] == 1, f"Failed adding the Hyperdrive deployer to the factory.\n{receipt=}"
    pool_config.baseToken = base_token_contract.address

    # Mint base and approve the initial liquidity amount for the hyperdrive factory
    _mint_and_approve(
        web3=web3,
        funding_account=deploy_account,
        funding_contract=base_token_contract,
        contract_to_approve=factory_contract,
        mint_amount=initial_liquidity,
    )

    # Deploy the Hyperdrive contract and call the initialize function
    hyperdrive_checksum_address = Web3.to_checksum_address(
        _deploy_and_initialize_hyperdrive_pool(
            web3,
            deployer_contract_addr,
            deploy_account,
            initial_liquidity,
            initial_fixed_rate,
            pool_contract_addr,
            pool_config,
            factory_contract,
        )
    )
    # Get block number when hyperdrive was deployed
    return DeployedHyperdrivePool(
        web3,
        deploy_account=deploy_account,
        hyperdrive_contract_addresses=HyperdriveAddresses(
            base_token=Web3.to_checksum_address(base_token_contract.address),
            hyperdrive_factory=Web3.to_checksum_address(factory_contract.address),
            mock_hyperdrive=hyperdrive_checksum_address,
            mock_hyperdrive_math=None,
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
    deploy_account_addr: ChecksumAddress,
    initial_variable_rate: FixedPoint,
    pool_config: PoolConfig,
    max_fees: Fees,
<<<<<<< HEAD
) -> tuple[ERC20MintableContract, ERC4626HyperdriveFactoryContract, ChecksumAddress, ChecksumAddress]:
=======
) -> tuple[Contract, Contract, ChecksumAddress, ChecksumAddress]:
>>>>>>> e5ca006 (finally fixed deployment)
    """Deploys the hyperdrive factory contract on the rpc_uri chain.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    deploy_account_addr: ChecksumAddress
        The address of the account that's deploying the contract.
    initial_variable_rate: FixedPoint
        The starting variable rate for an underlying yield source.
    pool_config: PoolConfig
        The configuration for initializing hyperdrive.
        The type is generated from the Hyperdrive ABI using Pypechain.
    max_fees: Fees
        The maximum value for the setup fees.

    Returns
    -------
    tuple[Contract, Contract, ChecksumAddress, ChecksumAddress]
<<<<<<< HEAD
        Containing the deployed base token, factory, the pool, and the deploy contracts/addresses.
    """
    erc20args = ERC20MintableContract.ConstructorArgs(
        name="Base", symbol="BASE", decimals=18, admin=ADDRESS_ZERO, isCompetitionMode_=False
    )
    base_token_contract = ERC20MintableContract.deploy(w3=web3, account=deploy_account_addr, constructorArgs=erc20args)

    pool = MockERC4626Contract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructorArgs=MockERC4626Contract.ConstructorArgs(
            asset=base_token_contract.address,
            name="Delvnet Yield Source",
            symbol="DELV",
            initialRate=initial_variable_rate.scaled_value,
            admin=ADDRESS_ZERO,
            isCompetitionMode=False,
=======
        Containing the deployed base token and factory contracts,
        as well as the pool and deployer contract addresses.
    """
    args = [
        "Base",  # name
        "BASE",  # symbol
        18,  # decimals
        ADDRESS_ZERO,  # admin_addr
        False,  # isCompetitionMode
    ]
    base_token_contract_addr, base_token_contract = deploy_contract(
        web3,
        abi=abis["ERC20Mintable"],
        bytecode=bytecodes["ERC20Mintable"],
        deploy_account_addr=deploy_account_addr,
        args=args,
    )
    args = [
        base_token_contract_addr,  # erc20_contract_addr
        "Delvnet Yield Source",  # name
        "DELV",  # symbol
        initial_variable_rate.scaled_value,  # initial_apr
        ADDRESS_ZERO,  # admin_addr
        False,  # isCompetitionMode
    ]
    pool_contract_addr, _ = deploy_contract(
        web3,
        abi=abis["MockERC4626"],
        bytecode=bytecodes["MockERC4626"],
        deploy_account_addr=deploy_account_addr,
        args=args,
    )
    forwarder_factory_contract_addr, forwarder_factory_contract = deploy_contract(
        web3,
        abi=abis["ForwarderFactory"],
        bytecode=bytecodes["ForwarderFactory"],
        deploy_account_addr=deploy_account_addr,
    )
    core_deployer_contract_addr, _ = deploy_contract(
        web3,
        abi=abis["ERC4626HyperdriveCoreDeployer"],
        bytecode=bytecodes["ERC4626HyperdriveCoreDeployer"],
        deploy_account_addr=deploy_account_addr,
    )
    target_0_deployer_addr, _ = deploy_contract(
        web3,
        abi=abis["ERC4626Target0Deployer"],
        bytecode=bytecodes["ERC4626Target0Deployer"],
        deploy_account_addr=deploy_account_addr,
    )
    target_1_deployer_addr, _ = deploy_contract(
        web3,
        abi=abis["ERC4626Target1Deployer"],
        bytecode=bytecodes["ERC4626Target1Deployer"],
        deploy_account_addr=deploy_account_addr,
    )
    deployer_contract_addr, _ = deploy_contract(
        web3,
        abi=abis["ERC4626HyperdriveDeployer"],
        bytecode=bytecodes["ERC4626HyperdriveDeployer"],
        deploy_account_addr=deploy_account_addr,
        args=(core_deployer_contract_addr, target_0_deployer_addr, target_1_deployer_addr),
    )
    _, factory_contract = deploy_contract(
        web3,
        abi=abis["HyperdriveFactory"],
        bytecode=bytecodes["HyperdriveFactory"],
        deploy_account_addr=deploy_account_addr,
        args=(
            (  # factory config
                deploy_account_addr,  # governance
                deploy_account_addr,  # hyperdriveGovernance
                [],  # defaultPausers (new address[](1))
                deploy_account_addr,  # feeCollector
                _dataclass_to_tuple(pool_config.fees),  # curve, flat, governance
                _dataclass_to_tuple(max_fees),  # max_curve, max_flat, max_governance
                forwarder_factory_contract_addr,  # Linker factory
                forwarder_factory_contract.functions.ERC20LINK_HASH().call(),  # linkerCodeHash
            ),
>>>>>>> e5ca006 (finally fixed deployment)
        ),
    )
    forwarder_factory_contract = ForwarderFactoryContract.deploy(
        w3=web3,
        account=deploy_account_addr,
    )
    core_deployer_contract = ERC4626HyperdriveCoreDeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
    )
    target0_contract = ERC4626Target0DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
    )
    target1_contract = ERC4626Target1DeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
    )
    deployer_contract = ERC4626HyperdriveDeployerContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        core_deployer_contract=core_deployer_contract.address,
        target0_contract=target0_contract.address,
        target1_contract=target1_contract.address,
        target2_contract=None,  # FIXME
        target3_contract=None,  # FIXME
    )
    factory_contract = ERC4626HyperdriveFactoryContract.deploy(
        w3=web3,
        account=deploy_account_addr,
        constructorArgs=ERC4626HyperdriveFactoryContract.ConstructorArgs(
            FactoryConfig(
                governance=deploy_account_addr,
                hyperdriveGovernance=deploy_account_addr,
                defaultPausers=[],
                feeCollector=deploy_account_addr,
                fees=pool_config.fees,
                maxFees=max_fees,
                linkerFactory=forwarder_factory_contract.address,
                linkerCodeHash=forwarder_factory_contract.functions.ERC20LINK_HASH().call(),
            ),
            sweepTargets=[],
        ),
    )
    return base_token_contract, factory_contract, pool.address, deployer_contract.address


def _mint_and_approve(
    web3,
    funding_account,
    funding_contract: Contract,
    contract_to_approve: Contract,
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
    deploy_contract_address: ChecksumAddress,
    deploy_account: LocalAccount,
    initial_liquidity: FixedPoint,
    initial_fixed_rate: FixedPoint,
    pool_contract_addr: ChecksumAddress,
    pool_config: PoolConfig,
    factory_contract: ERC4626HyperdriveFactoryContract,
) -> str:
    """Deploys the hyperdrive factory contract on the rpc_uri chain.

    Arguments
    ---------
    web3: Web3
        Web3 provider object.
    deploy_contract_address: ChecksumAddress
        The address for the deployed ERC4626HyperdriveDeployer contract.
    deploy_account: LocalAccount
        A Web3 LocalAccount for the given private key.
    initial_liquidity: FixedPoint
        The amount of money to be provided by the `deploy_account` for initial pool liquidity.
    initial_fixed_rate: FixedPoint
        The fixed rate of the pool on initialization.
    pool_contract_addr: ChecksumAddress
        The address of the pool contract.
    pool_config: PoolConfig
        The configuration for initializing hyperdrive.
        The type is generated from the Hyperdrive ABI using Pypechain.
    factory_contract: Contract
        The hyperdrive factory contract.

    Returns
    -------
    str
        The deployed hyperdrive contract address.
    """
<<<<<<< HEAD

    deploy_and_init_function = factory_contract.functions.deployAndInitialize(
=======
    fn_args = (
>>>>>>> e5ca006 (finally fixed deployment)
        deploy_contract_address,  # hyperdriveDeployer
        pool_config,  # poolConfig
        encode(("address", "address[]"), (pool_contract_addr, [])),  # abi.encode(address(pool), new address[](0))
        initial_liquidity.scaled_value,
        initial_fixed_rate.scaled_value,
        bytes(0),  # new bytes(0)
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
