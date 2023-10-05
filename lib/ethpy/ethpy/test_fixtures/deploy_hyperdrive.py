"""Functions to initialize hyperdrive using web3"""
from __future__ import annotations

from dataclasses import dataclass, fields, is_dataclass

from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import Address
from ethpy.base import (
    deploy_contract,
    deploy_contract_and_return,
    get_transaction_logs,
    initialize_web3_with_http_provider,
    load_all_abis,
    smart_contract_transact,
)
from fixedpointmath import FixedPoint
from hypertypes.IHyperdriveTypes import Fees, PoolConfig
from web3 import Web3
from web3.contract.contract import Contract

# TODO these functions should eventually be moved to `ethpy/hyperdrive`, but leaving
# these here for now to be used by tests while we figure out how to parameterize
# initial hyperdrive conditions


def _dataclass_to_tuple(instance: dataclass) -> tuple:
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


# Following solidity implementation here, so matching function name
def _calculateTimeStretch(apr: int) -> int:  # pylint: disable=invalid-name
    """Helper function mirroring solidity calculateTimeStretch

    Arguments
    ---------
    apr : int
        The scaled input apr

    Returns
    -------
    int
        The scaled output time stretch
    """
    fp_apr = FixedPoint(scaled_value=apr)
    time_stretch = FixedPoint("5.24592") / (FixedPoint("0.04665") * (fp_apr * 100))
    return (FixedPoint(1) / time_stretch).scaled_value


def initialize_deploy_account(web3: Web3) -> LocalAccount:
    """Initializes the local anvil account to deploy everything from.

    Arguments
    ---------
    web3 : Web3
        web3 provider object

    Returns
    -------
    LocalAccount
        The LocalAccount object
    """
    # TODO get private key of this account programmatically
    # https://github.com/delvtech/elf-simulations/issues/816
    # This is the private key of account 0 of the anvil pre-funded account
    account_private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    account: LocalAccount = Account().from_key(account_private_key)
    # Ensure this private key is actually matched to the first address of anvil
    assert web3.eth.accounts[0] == account.address
    return account


def deploy_hyperdrive_factory(rpc_uri: str, deploy_account: LocalAccount) -> tuple[Contract, Contract]:
    """Deploys the hyperdrive factory contract on the rpc_uri chain.

    Arguments
    ---------
    rpc_uri: str
        The RPC URI of the chain
    deploy_account: LocalAccount
        The account that deploys the contracts

    Returns
    -------
    tuple[Contract, Contract]
        The base token contract and the factory contract respectively
    """
    # TODO parameterize these parameters
    # pylint: disable=too-many-locals
    # Initial factory settings
    initial_variable_rate = FixedPoint("0.05").scaled_value
    curve_fee = FixedPoint("0.1").scaled_value  # 10%
    flat_fee = FixedPoint("0.0005").scaled_value  # 0.05%
    governance_fee = FixedPoint("0.15").scaled_value  # 15%
    max_curve_fee = FixedPoint("0.3").scaled_value  # 30%
    max_flat_fee = FixedPoint("0.0015").scaled_value  # 0.15%
    max_governance_fee = FixedPoint("0.30").scaled_value  # 30%
    # Configuration settings
    abi_folder = "packages/hyperdrive/src/abis/"

    # Load compiled objects
    abis, bytecodes = load_all_abis(abi_folder, return_bytecode=True)
    web3 = initialize_web3_with_http_provider(rpc_uri, reset_provider=False)
    # Convert deploy address to checksum address
    deploy_account_addr = Web3.to_checksum_address(deploy_account.address)

    # Deploy contracts
    base_token_contract_addr, base_token_contract = deploy_contract_and_return(
        web3,
        abi=abis["ERC20Mintable"],
        bytecode=bytecodes["ERC20Mintable"],
        deploy_account_addr=deploy_account_addr,
    )
    pool_contract_addr = deploy_contract(
        web3,
        abi=abis["MockERC4626"],
        bytecode=bytecodes["MockERC4626"],
        deploy_account_addr=deploy_account_addr,
        args=[base_token_contract_addr, "Delvnet Yield Source", "DELV", initial_variable_rate],
    )
    forwarder_factory_contract_addr, forwarder_factory_contract = deploy_contract_and_return(
        web3,
        abi=abis["ForwarderFactory"],
        bytecode=bytecodes["ForwarderFactory"],
        deploy_account_addr=deploy_account_addr,
    )
    deployer_contract_addr = deploy_contract(
        web3,
        abi=abis["ERC4626HyperdriveDeployer"],
        bytecode=bytecodes["ERC4626HyperdriveDeployer"],
        deploy_account_addr=deploy_account_addr,
        args=[pool_contract_addr],
    )

    # Set args and deploy factory
    # Calling solidity factory with deployer account as governance and fee collector
    factory_config = (
        deploy_account_addr,  # governance
        deploy_account_addr,  # hyperdriveGovernance
        deploy_account_addr,  # feeCollector
        (curve_fee, flat_fee, governance_fee),  # fees
        (max_curve_fee, max_flat_fee, max_governance_fee),  # maxFees
        [],  # defaultPausers (new address[](1))
    )
    forwarder_factory_link_hash = forwarder_factory_contract.functions.ERC20LINK_HASH().call()
    empty_list_array = []  # new address[](0)
    _, factory_contract = deploy_contract_and_return(
        web3,
        abi=abis["ERC4626HyperdriveFactory"],
        bytecode=bytecodes["ERC4626HyperdriveFactory"],
        deploy_account_addr=deploy_account_addr,
        args=[
            factory_config,
            deployer_contract_addr,
            forwarder_factory_contract_addr,
            forwarder_factory_link_hash,
            pool_contract_addr,
            empty_list_array,
        ],
    )

    return base_token_contract, factory_contract


def deploy_and_initialize_hyperdrive(
    web3: Web3,
    base_token_contract: Contract,
    factory_contract: Contract,
    deploy_account: LocalAccount,
    initial_contribution=FixedPoint(100_000_000).scaled_value,
) -> Address:
    """Calls the hyperdrive factory to deploy and initialize new hyperdrive contract

    Arguments
    ---------
    web3 : Web3
        web3 provider object
    base_token_contract : Contract
        The base token contract
    factory_contract : Contract
        The hyperdrive factory contract
    deploy_account: LocalAccount
        The account that deploys the contracts

    Returns
    -------
    str
        The deployed hyperdrive contract address
    """
    # TODO parameterize these parameters
    # pylint: disable=too-many-locals
    # Initial hyperdrive settings
    initial_share_price = FixedPoint(1).scaled_value
    minimum_share_reserves = FixedPoint(10).scaled_value
    minimum_transaction_amount = FixedPoint(1 * 10**15).scaled_value
    position_duration = 604800  # 1 week
    checkpoint_duration = 3600  # 1 hour
    time_stretch = _calculateTimeStretch(FixedPoint("0.05").scaled_value)
    oracle_size = 10
    update_gap = 3600  # 1 hour
    initial_fixed_rate = FixedPoint("0.05").scaled_value

    deploy_account_addr = Web3.to_checksum_address(deploy_account.address)

    # Mint base tokens
    # Need to pass signature instead of function name since multiple mint functions
    tx_receipt = smart_contract_transact(
        web3, base_token_contract, deploy_account, "mint(address,uint256)", deploy_account_addr, initial_contribution
    )
    tx_receipt = smart_contract_transact(
        web3, base_token_contract, deploy_account, "approve", factory_contract.address, initial_contribution
    )

    # Call factory to make hyperdrive market
    # Some of these pool info configurations don't do anything, as the factory is overwriting them
    # Using the Pypechain generated HyperdriveTypes for PoolConfig to ensure the ordering & type safety
    pool_config = PoolConfig(
        base_token_contract.address,
        initial_share_price,
        minimum_share_reserves,
        minimum_transaction_amount,
        position_duration,
        checkpoint_duration,
        time_stretch,
        deploy_account_addr,  # governance, overwritten by factory
        deploy_account_addr,  # feeCollector, overwritten by factory
        Fees(0, 0, 0),  # fees, overwritten by factory
        oracle_size,  # oracleSize
        update_gap,
    )
    # Function arguments
    fn_args = (
        _dataclass_to_tuple(pool_config),
        [],  # new bytes[](0)
        initial_contribution,
        initial_fixed_rate,  # fixedRate
    )
    tx_receipt = smart_contract_transact(
        web3,  # web3
        factory_contract,  # contract
        deploy_account,  # signer
        "deployAndInitialize",  # function_name_or_signature
        *fn_args,
    )

    logs = get_transaction_logs(factory_contract, tx_receipt)
    hyperdrive_address = None
    for log in logs:
        if log["event"] == "GovernanceUpdated":
            hyperdrive_address = log["address"]
    if hyperdrive_address is None:
        raise AssertionError("Generating hyperdrive contract didn't return address")

    return hyperdrive_address
