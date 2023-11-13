"""Helper functions for deploying Hyperdrive contracts."""
from __future__ import annotations

from dataclasses import fields, is_dataclass
from typing import Any, NamedTuple

from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import ChecksumAddress
from ethpy.base import get_transaction_logs, initialize_web3_with_http_provider, load_all_abis, smart_contract_transact
from ethpy.base.contract import deploy_contract
from fixedpointmath import FixedPoint
from hypertypes.IHyperdriveTypes import Fees, PoolConfig
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


def deploy_hyperdrive_from_factory(
    rpc_uri: str,
    abi_folder: str,
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
    rpc_uri : str
        The URI of the local RPC node.
    abi_folder : str
        The local directory that contains all ABI JSON files.
    deployer_private_key : str
        Private key for the funded wallet for deploying Hyperdrive.
    initial_liquidity : FixedPoint
        The amount of money to be provided by the `deploy_account` for initial pool liquidity.
    initial_variable_rate: FixedPoint
        The starting variable rate for an underlying yield source.
    initial_fixed_rate : FixedPoint
        The fixed rate of the pool on initialization.
    pool_config : PoolConfig
        The configuration for initializing hyperdrive.
        The type is generated from the Hyperdrive ABI using Pypechain.
    max_fees : Fees
        The maximum value for the setup fees.

    Returns
    -------
    LocalHyperdriveChain
        A named tuple with the following fields:
            web3 : Web3
                Web3 provider object.
            deploy_account : LocalAccount
                The local account that deploys and initializes hyperdrive.
            hyperdrive_contract_addresses: HyperdriveAddresses
                The hyperdrive contract addresses.
            hyperdrive_contract : Contract
                Web3 contract instance for the hyperdrive contract.
            hyperdrive_factory_contract : Contract
                Web3 contract instance for the hyperdrive factory contract.
            base_token_contract : Contract
                Web3 contract instance for the base token contract.
    """
    # Contract calls use the web3.py interface
    web3 = initialize_web3_with_http_provider(rpc_uri, reset_provider=False)
    # Create the pre-funded account on the Delv devnet
    deploy_account = _initialize_deployment_account(web3, deployer_private_key)
    deploy_account_addr = Web3.to_checksum_address(deploy_account.address)
    # Fill in the pool config information for the deployer account address
    pool_config.governance = deploy_account_addr
    pool_config.feeCollector = deploy_account_addr
    # Load the ABI and Bytecode information for all files in the ABI folder
    # This must include the following:
    # ERC20Mintable, MockERC4626, ForwarderFactory, ERC4626HyperdriveDeployer, ERC4626HyperdriveFactory
    abis, bytecodes = load_all_abis(abi_folder, return_bytecode=True)
    # Deploy the factory and base token contracts
    base_token_contract, factory_contract, pool_contract_addr = _deploy_hyperdrive_factory(
        web3,
        deploy_account_addr,
        abis,
        bytecodes,
        initial_variable_rate,
        pool_config,
        max_fees,
    )
    pool_config.baseToken = base_token_contract.address
    # Mint base and approve the initial liquidity amount for the hyperdrive factory
    _ = _mint_and_approve(
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
            deploy_account,
            initial_liquidity,
            initial_fixed_rate,
            pool_contract_addr,
            pool_config,
            factory_contract,
        )
    )
    return DeployedHyperdrivePool(
        web3,
        deploy_account=deploy_account,
        hyperdrive_contract_addresses=HyperdriveAddresses(
            base_token=Web3.to_checksum_address(base_token_contract.address),
            hyperdrive_factory=Web3.to_checksum_address(factory_contract.address),
            mock_hyperdrive=hyperdrive_checksum_address,
            mock_hyperdrive_math=None,
        ),
        hyperdrive_contract=web3.eth.contract(address=hyperdrive_checksum_address, abi=abis["IHyperdrive"]),
        hyperdrive_factory_contract=factory_contract,
        base_token_contract=base_token_contract,
    )


def _dataclass_to_tuple(instance: Any) -> tuple:
    """Resursively convert the input Dataclass to a tuple.

    Iterate over the fields of the dataclass and compiles them into a tuple.
    Check if the type of a field is also a dataclass, and if so, recursively convert it to a tuple.
    This method preserves the attribute ordering.

    Arguments
    ---------
    instance : dataclass
        A dataclass, whose fields could contain other dataclasses.

    Returns
    -------
    tuple
        A nested tuple of all dataclass fields.
    """
    if not is_dataclass(instance):
        return instance
    return tuple(_dataclass_to_tuple(getattr(instance, field.name)) for field in fields(instance))


def _initialize_deployment_account(web3: Web3, account_private_key: str) -> LocalAccount:
    """Initializes the local anvil account to deploy everything from.

    Arguments
    ---------
    web3 : Web3
        Web3 provider object.
    account_private_key : str
        Private key for the funded wallet for deploying Hyperdrive.

    Returns
    -------
    LocalAccount
        A Web3 LocalAccount for the given private key.

    .. todo::
        get private key for `account_private_key` of this account programmatically
        https://github.com/delvtech/elf-simulations/issues/816
        This is the private key of account 0 of the anvil pre-funded account
    """
    account: LocalAccount = Account().from_key(account_private_key)
    # Ensure this private key is actually matched to the first address of anvil
    assert web3.eth.accounts[0] == account.address
    return account


def _deploy_hyperdrive_factory(
    web3: Web3,
    deploy_account_addr: ChecksumAddress,
    abis: dict,
    bytecodes: dict,
    initial_variable_rate: FixedPoint,
    pool_config: PoolConfig,
    max_fees: Fees,
) -> tuple[Contract, Contract, ChecksumAddress]:
    """Deploys the hyperdrive factory contract on the rpc_uri chain.

    Arguments
    ---------
    web3 : Web3
        Web3 provider object.
    deploy_account_addr : ChecksumAddress
        The address of the account that's deploying the contract.
    abis : dict
        A dictionary, keyed by the Hyperdrive ABI filename, containing the ABI JSON dictionary for each file.
    bytecodes : dict
        A dictionary, keyed by the Hyperdrive ABI filename, containing the contract bytecode for each file.
    initial_variable_rate : FixedPoint
        The starting variable rate for an underlying yield source.
    pool_config : PoolConfig
        The configuration for initializing hyperdrive.
        The type is generated from the Hyperdrive ABI using Pypechain.
    max_fees : Fees
        The maximum value for the setup fees.

    Returns
    -------
    (base_token_contract, factory_token_contract) : tuple[Contract, Contract]
        Containing he deployed base token and factory contracts.
    """
    # args = [name, symbol, decimals, admin_addr, isCompetitionMode]
    args = ["Base", "BASE", 18, ADDRESS_ZERO, False]
    base_token_contract_addr, base_token_contract = deploy_contract(
        web3,
        abi=abis["ERC20Mintable"],
        bytecode=bytecodes["ERC20Mintable"],
        deploy_account_addr=deploy_account_addr,
        args=args,
    )
    # args = [erc20_contract_addr, name, symbol, initial_apr, admin_addr, isCompetitionMode]
    args = [
        base_token_contract_addr,
        "Delvnet Yield Source",
        "DELV",
        initial_variable_rate.scaled_value,
        ADDRESS_ZERO,
        False,
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
    deployer_contract_addr, _ = deploy_contract(
        web3,
        abi=abis["ERC4626HyperdriveDeployer"],
        bytecode=bytecodes["ERC4626HyperdriveDeployer"],
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

    _, factory_contract = deploy_contract(
        web3,
        abi=abis["ERC4626HyperdriveFactory"],
        bytecode=bytecodes["ERC4626HyperdriveFactory"],
        deploy_account_addr=deploy_account_addr,
        args=[
            (  # factory config
                deploy_account_addr,  # governance
                deploy_account_addr,  # hyperdriveGovernance
                [],  # defaultPausers (new address[](1))
                deploy_account_addr,  # feeCollector
                _dataclass_to_tuple(pool_config.fees),  # curve, flat, governance
                _dataclass_to_tuple(max_fees),  # max_curve, max_flat, max_governance
                deployer_contract_addr,  # Hyperdrive deployer
                target_0_deployer_addr,
                target_1_deployer_addr,
                forwarder_factory_contract_addr,  # Linker factory
                forwarder_factory_contract.functions.ERC20LINK_HASH().call(),  # linkerCodeHash
            ),
            [],  # new address[](0)
        ],
    )
    return base_token_contract, factory_contract, pool_contract_addr


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
    web3 : Web3
        Web3 provider object.
    funding_account : LocalAccount
        A Web3 LocalAccount for the given private key.
    funding_contract : Contract
        Web3 contract instance for the contract used to mint tokens.
    contract_to_approve : Contract
        Web3 contract instance for the contract that needs approval from the funding contract.
    mint_amount : FixedPoint
        The amount to mint and approve.

    Returns
    -------
    tuple[TxReceipt, TxReceipt]
        The (mint, approval) transaction receipts.

    """
    # Need to pass signature instead of function name since multiple mint functions
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
    deploy_account: LocalAccount,
    initial_liquidity: FixedPoint,
    initial_fixed_rate: FixedPoint,
    pool_contract_addr: ChecksumAddress,
    pool_config: PoolConfig,
    factory_contract: Contract,
) -> str:
    """Deploys the hyperdrive factory contract on the rpc_uri chain.

    Arguments
    ---------
    web3 : Web3
        Web3 provider object.
    deploy_account : LocalAccount
        A Web3 LocalAccount for the given private key.
    initial_liquidity : FixedPoint
        The amount of money to be provided by the `deploy_account` for initial pool liquidity.
    initial_fixed_rate : FixedPoint
        The fixed rate of the pool on initialization.
    pool_config : PoolConfig
        The configuration for initializing hyperdrive.
        The type is generated from the Hyperdrive ABI using Pypechain.
    factory_contract : Contract
        The hyperdrive factory contract.

    Returns
    -------
    str
        The deployed hyperdrive contract address.
    """
    fn_args = (
        _dataclass_to_tuple(pool_config),
        initial_liquidity.scaled_value,
        initial_fixed_rate.scaled_value,
        bytes(0),  # new bytes(0)
        [],  # new bytes32[](0)
        pool_contract_addr,
    )
    tx_receipt = smart_contract_transact(
        web3,  # web3
        factory_contract,  # contract
        deploy_account,  # signer
        "deployAndInitialize",  # function_name_or_signature
        *fn_args,
    )
    logs = get_transaction_logs(factory_contract, tx_receipt)
    hyperdrive_address: str | None = None
    for log in logs:
        if log["event"] == "GovernanceUpdated":
            hyperdrive_address = log["address"]
    if hyperdrive_address is None:
        raise AssertionError("Generating hyperdrive contract didn't return address")
    return hyperdrive_address
