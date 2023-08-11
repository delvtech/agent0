import subprocess
import time
from typing import Any

import pytest
from ethpy.base import initialize_web3_with_http_provider

from .deploy_hyperdrive import deploy_and_initialize_hyperdrive, deploy_hyperdrive_factory, initialize_deploy_account


@pytest.fixture(scope="function")
def local_chain():
    """Launches a local anvil chain for testing.
    Returns the chain url

    """
    anvil_port = 9999
    host = "127.0.0.1"  # localhost

    # Assuming anvil command is accessable in path
    # running into issue with contract size without --code-size-limit arg
    anvil_process = subprocess.Popen(
        ["anvil", "--host", "127.0.0.1", "--port", str(anvil_port), "--code-size-limit", "9999999999"]
    )
    local_chain_ = "http://" + host + ":" + str(anvil_port)

    # Hack, wait for anvil chain to initialize
    time.sleep(3)

    yield local_chain_

    # Kill anvil process at end
    anvil_process.kill()


@pytest.fixture(scope="function")
def hyperdrive_chain(local_chain):
    """Initializes hyperdrive on a local anvil chain for testing.
    Returns the hyperdrive contract address

    """
    web3 = initialize_web3_with_http_provider(local_chain, reset_provider=False)
    account = initialize_deploy_account(web3)
    base_token_contract, factory_contract = deploy_hyperdrive_factory(local_chain, account)
    return deploy_and_initialize_hyperdrive(web3, base_token_contract, factory_contract, account)

    ## TODO this is currently assuming pytest is ran from outermost directory
    ## If we want to allow for pytest to run in this subpackage, we'll need to change the location of this
    # abi_folder = "packages/hyperdrive/src/abis/"

    ## Load compiled objects
    # abis, bytecodes = load_all_abis(abi_folder, return_bytecode=True)

    # web3 = initialize_web3_with_http_provider(local_chain_, reset_provider=False)
    ## Set pre-funded account as sender
    # deploy_addr = web3.eth.accounts[0]
    ## TODO get private key of this account
    # account_private_key = "0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80"
    # deploy_agent = EthAgent(Account().from_key(account_private_key))

    ## Initial parameters
    # initial_variable_rate = int(0.05e18)
    # initial_share_price = int(1e18)
    # minimum_share_price = int(10e18)
    # position_duration = 604800  # 1 week
    # checkpoint_duration = 3600  # 1 hour
    # time_stretch = calculateTimeStretch(int(0.05e18))

    # curve_fee = int(0.1e18)  # 10%
    # flat_fee = int(0.0005e18)  # flat 0.05
    # governance_fee = int(0.15e18)

    # oracle_size = 10
    # update_gap = 3600  # 1 hour
    # initial_contribution = int(100_000_000e18)
    # initial_fixed_rate = int(0.05e18)

    ## Deploy contracts
    # base_token_addr, base_token_contract = deploy_contract(
    #    web3,
    #    abi=abis["ERC20Mintable"],
    #    bytecode=bytecodes["ERC20Mintable"],
    #    deploy_addr=deploy_addr,
    #    return_contract=True,
    # )

    # pool_addr = deploy_contract(
    #    web3,
    #    abi=abis["MockERC4626"],
    #    bytecode=bytecodes["MockERC4626"],
    #    deploy_addr=deploy_addr,
    #    args=[base_token_addr, "Delvnet Yield Source", "DELV", initial_variable_rate],
    #    return_contract=False,
    # )

    # forwarder_factory_addr, forwarder_factory_contract = deploy_contract(
    #    web3,
    #    abi=abis["ForwarderFactory"],
    #    bytecode=bytecodes["ForwarderFactory"],
    #    deploy_addr=deploy_addr,
    #    return_contract=True,
    # )

    # deployer_addr = deploy_contract(
    #    web3,
    #    abi=abis["ERC4626HyperdriveDeployer"],
    #    bytecode=bytecodes["ERC4626HyperdriveDeployer"],
    #    deploy_addr=deploy_addr,
    #    args=[pool_addr],
    #    return_contract=False,
    # )

    # factory_config = (
    #    deploy_addr,  # governance
    #    deploy_addr,  # hyperdriveGovernance
    #    deploy_addr,  # feeCollector
    #    (  # fees
    #        int(0.1e18),  # curve 10%
    #        int(0.0005e18),  # flat 0.05%
    #        int(0.15e18),  # governance 0.15%
    #    ),
    #    (  # maxFees
    #        int(0.3e18),  # curve 30%
    #        int(0.0015e18),  # flat 0.15%
    #        int(0.30e18),  # governance 0.30%
    #    ),
    #    [],  # defaultPausers (new address[](1))
    # )
    # forwarder_factory_link_hash = forwarder_factory_contract.functions.ERC20LINK_HASH().call()
    # empty_list_array = []  # new address[](0)
    # factory_addr, factory_contract = deploy_contract(
    #    web3,
    #    abi=abis["ERC4626HyperdriveFactory"],
    #    bytecode=bytecodes["ERC4626HyperdriveFactory"],
    #    deploy_addr=deploy_addr,
    #    args=[
    #        factory_config,
    #        deployer_addr,
    #        forwarder_factory_addr,
    #        forwarder_factory_link_hash,
    #        pool_addr,
    #        empty_list_array,
    #    ],
    #    return_contract=True,
    # )

    ## Mint base tokens
    ## Need to pass signature instead of function name since multiple mint functions
    # tx_receipt = smart_contract_transact(
    #    web3, base_token_contract, deploy_agent, "mint(address,uint256)", deploy_addr, initial_contribution
    # )
    # tx_receipt = smart_contract_transact(
    #    web3, base_token_contract, deploy_agent, "approve", factory_addr, initial_contribution
    # )

    ## Call factory to make hyperdrive market
    ## Some of these are already defined in FactoryConfig, were those defaults?
    # pool_config = (
    #    base_token_addr,
    #    initial_share_price,
    #    minimum_share_price,
    #    position_duration,
    #    checkpoint_duration,
    #    time_stretch,
    #    deploy_addr,  # governance
    #    deploy_addr,  # feeCollector
    #    (  # fees
    #        curve_fee,
    #        flat_fee,  # flat 0.05%
    #        governance_fee,  # governance 0.15%
    #    ),
    #    oracle_size,  # oracleSize
    #    update_gap,
    # )
    # tx_receipt = smart_contract_transact(
    #    web3,
    #    factory_contract,
    #    deploy_agent,
    #    "deployAndInitialize",
    #    # Function arguments
    #    pool_config,
    #    [],  # new bytes[](0)
    #    initial_contribution,
    #    initial_fixed_rate,  # fixedRate
    # )

    # logs = get_transaction_logs(factory_contract, tx_receipt)
    # hyperdrive_address = None
    # for log in logs:
    #    if log["event"] == "GovernanceUpdated":
    #        hyperdrive_address = log["address"]
    # if hyperdrive_address is None:
    #    raise AssertionError("Generating hyperdrive contract didn't return address")
