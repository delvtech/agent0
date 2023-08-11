"""Functions to initialize hyperdrive using web3"""

from eth_account.account import Account
from eth_account.signers.local import LocalAccount
from ethpy.base import (
    deploy_contract,
    deploy_contract_and_return,
    get_transaction_logs,
    initialize_web3_with_http_provider,
    load_all_abis,
    smart_contract_transact,
)
from fixedpointmath import FixedPoint
from web3 import Web3
from web3.contract.contract import Contract

# TODO these functions should eventually be moved to `ethpy/hyperdrive`, but leaving
# these here for now to be used by tests while we figure out how to parameterize
# initial hyperdrive conditions


# Following solidity implementation here, so matching function name
def _calculateTimeStretch(apr: int) -> int:  # pylint: disable=invalid-name
    """Helper function mirroring solidity calculateTimeStretch

    Arguments
    --------
    apr: int
        The scaled input apr

    Returns
    -------
    int
        The scaled output time stretch
    """
    fp_apr = FixedPoint(scaled_value=apr)
    time_stretch = FixedPoint(scaled_value=int(5.24592e18)) / (
        FixedPoint(scaled_value=int(0.04665e18)) * (fp_apr * 100)
    )
    return (FixedPoint(scaled_value=int(1e18)) / time_stretch).scaled_value


def initialize_deploy_account(web3: Web3) -> LocalAccount:
    """Initializes the local anvil account to deploy everything from.

    Arguments
    --------
    web3 : Web3
        web3 provider object

    Returns
    -------
    LocalAccount
        The LocalAccount object
    """
    # TODO get private key of this account programatically
    # This is the private key of account 0 of the anvil prefunded account
    account_private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    account: LocalAccount = Account().from_key(account_private_key)
    # Ensure this private key is actually matched to the first address of anvil
    assert web3.eth.accounts[0] == account.address
    return account


def deploy_hyperdrive_factory(rpc_url: str, deploy_account: LocalAccount) -> tuple[Contract, Contract]:
    """Deploys the hyperdrive factory contract on the rpc_url chain

    Arguments
    --------
    rpc_url: str
        The RPC URL of the chain
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
    initial_variable_rate = int(0.05e18)
    curve_fee = int(0.1e18)  # 10%
    flat_fee = int(0.0005e18)  # 0.05%
    governance_fee = int(0.15e18)  # 0.15%
    max_curve_fee = int(0.3e18)  # 30%
    max_flat_fee = int(0.0015e18)  # 0.15%
    max_governance_fee = int(0.30e18)  # 0.30%
    # Configuration settings
    abi_folder = "packages/hyperdrive/src/abis/"

    # Load compiled objects
    abis, bytecodes = load_all_abis(abi_folder, return_bytecode=True)
    web3 = initialize_web3_with_http_provider(rpc_url, reset_provider=False)
    # Convert deploy address to checksum address
    deploy_addr = Web3.to_checksum_address(deploy_account.address)

    # Deploy contracts
    base_token_addr, base_token_contract = deploy_contract_and_return(
        web3,
        abi=abis["ERC20Mintable"],
        bytecode=bytecodes["ERC20Mintable"],
        deploy_addr=deploy_addr,
    )

    pool_addr = deploy_contract(
        web3,
        abi=abis["MockERC4626"],
        bytecode=bytecodes["MockERC4626"],
        deploy_addr=deploy_addr,
        args=[base_token_addr, "Delvnet Yield Source", "DELV", initial_variable_rate],
    )

    forwarder_factory_addr, forwarder_factory_contract = deploy_contract_and_return(
        web3,
        abi=abis["ForwarderFactory"],
        bytecode=bytecodes["ForwarderFactory"],
        deploy_addr=deploy_addr,
    )

    deployer_addr = deploy_contract(
        web3,
        abi=abis["ERC4626HyperdriveDeployer"],
        bytecode=bytecodes["ERC4626HyperdriveDeployer"],
        deploy_addr=deploy_addr,
        args=[pool_addr],
    )

    factory_config = (
        deploy_addr,  # governance
        deploy_addr,  # hyperdriveGovernance
        deploy_addr,  # feeCollector
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
        deploy_addr=deploy_addr,
        args=[
            factory_config,
            deployer_addr,
            forwarder_factory_addr,
            forwarder_factory_link_hash,
            pool_addr,
            empty_list_array,
        ],
    )

    return base_token_contract, factory_contract


def deploy_and_initialize_hyperdrive(
    web3: Web3,
    base_token_contract: Contract,
    factory_contract: Contract,
    deploy_account: LocalAccount,
) -> str:
    """Calls the hyperdrive factory to deploy and initialize new hyperdrive contract

    Arguments
    --------
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
    initial_contribution = int(100_000_000e18)
    initial_share_price = int(1e18)
    minimum_share_reserves = int(10e18)
    position_duration = 604800  # 1 week
    checkpoint_duration = 3600  # 1 hour
    time_stretch = _calculateTimeStretch(int(0.05e18))
    oracle_size = 10
    update_gap = 3600  # 1 hour
    initial_fixed_rate = int(0.05e18)

    deploy_addr = Web3.to_checksum_address(deploy_account.address)

    # Mint base tokens
    # Need to pass signature instead of function name since multiple mint functions
    tx_receipt = smart_contract_transact(
        web3, base_token_contract, deploy_account, "mint(address,uint256)", deploy_addr, initial_contribution
    )
    tx_receipt = smart_contract_transact(
        web3, base_token_contract, deploy_account, "approve", factory_contract.address, initial_contribution
    )

    # Call factory to make hyperdrive market
    # Some of these pool info configurations don't do anything, as the factory is overwriting them
    pool_config = (
        base_token_contract.address,
        initial_share_price,
        minimum_share_reserves,
        position_duration,
        checkpoint_duration,
        time_stretch,
        deploy_addr,  # governance, overwritten by factory
        deploy_addr,  # feeCollector, overwritten by factory
        (0, 0, 0),  # fees, overwritten by factory
        oracle_size,  # oracleSize
        update_gap,
    )
    tx_receipt = smart_contract_transact(
        web3,
        factory_contract,
        deploy_account,
        "deployAndInitialize",
        # Function arguments
        pool_config,
        [],  # new bytes[](0)
        initial_contribution,
        initial_fixed_rate,  # fixedRate
    )

    logs = get_transaction_logs(factory_contract, tx_receipt)
    hyperdrive_address = None
    for log in logs:
        if log["event"] == "GovernanceUpdated":
            hyperdrive_address = log["address"]
    if hyperdrive_address is None:
        raise AssertionError("Generating hyperdrive contract didn't return address")

    # TODO do I return the contract or address here?
    return hyperdrive_address
