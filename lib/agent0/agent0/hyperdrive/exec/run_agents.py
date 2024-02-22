"""Runner script for agents"""

from __future__ import annotations

import asyncio
import logging
import os
import random
import time
from typing import TYPE_CHECKING

from chainsync.db.api import balance_of, register_username
from eth_typing import BlockNumber
from ethpy import build_eth_config
from ethpy.hyperdrive import (
    AssetIdPrefix,
    HyperdriveReadWriteInterface,
    encode_asset_id,
    fetch_hyperdrive_address_from_uri,
)
from fixedpointmath import FixedPoint
from hexbytes import HexBytes

from agent0.base import Quantity, TokenType
from agent0.base.config import DEFAULT_USERNAME
from agent0.hyperdrive import HyperdriveWallet, Long, Short

from .create_and_fund_user_account import create_and_fund_user_account
from .fund_agents import async_fund_agents
from .setup_experiment import setup_experiment
from .trade_loop import trade_if_new_block

if TYPE_CHECKING:
    import pandas as pd
    from ethpy import EthConfig
    from ethpy.hyperdrive import HyperdriveAddresses
    from hypertypes import ERC20MintableContract, IERC4626HyperdriveContract

    from agent0 import AccountKeyConfig
    from agent0.base.config import AgentConfig, EnvironmentConfig
    from agent0.hyperdrive import HyperdriveAgent

START_LATENCY = 1
BACKOFF = 2


# TODO: These functions might be able to have their arguments simplified, but for now we will ignore.
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals


def setup_and_run_agent_loop(
    environment_config: EnvironmentConfig,
    agent_config: list[AgentConfig],
    account_key_config: AccountKeyConfig,
    eth_config: EthConfig | None = None,
    contract_addresses: HyperdriveAddresses | None = None,
    load_wallet_state: bool = True,
    liquidate: bool = False,
    minimum_avg_agent_base: FixedPoint | None = None,
) -> None:
    """Entrypoint to run agent trades in a loop.

    Arguments
    ---------
    environment_config: EnvironmentConfig
        The agent's environment configuration.
    agent_config: list[AgentConfig]
        The list of agent configurations to run.
    account_key_config: AccountKeyConfig
        Dataclass containing configuration options for the agent account, including keys and budgets.
    eth_config: EthConfig | None, optional
        Configuration for URIs to the rpc and artifacts.
        If not set, will look for the config in eth.env.
    contract_addresses: HyperdriveAddresses | None, optional
        Configuration for the URIs to the Hyperdrive contract addresses.
        If not set, will look for the addresses in eth_config.
    load_wallet_state: bool, optional
        If set, will connect to the db api to load wallet states from the current chain.
        Defaults to True.
    liquidate: bool, optional
        If set, will ignore all policy settings and liquidate all open positions.
        Defaults to False.
    minimum_avg_agent_base: FixedPoint, optional
        If set, then the script will fund the agents with their original budgets
        whenever the average balance across wallets is less than this amount.
    """
    # Set sane logging defaults to avoid spam from dependencies
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("web3").setLevel(logging.WARNING)
    # Setup and fund agents, create the interface, handle optional values
    interface, agent_accounts, eth_config, contract_addresses = setup_agents(
        environment_config,
        agent_config,
        account_key_config,
        eth_config,
        contract_addresses,
        load_wallet_state,
        liquidate,
    )
    # Run the agent trades in a while True loop
    run_agents(
        environment_config,
        eth_config,
        account_key_config,
        contract_addresses,
        interface,
        agent_accounts,
        liquidate,
        minimum_avg_agent_base,
    )


def setup_agents(
    environment_config: EnvironmentConfig,
    agent_config: list[AgentConfig],
    account_key_config: AccountKeyConfig,
    eth_config: EthConfig | None = None,
    contract_addresses: HyperdriveAddresses | None = None,
    load_wallet_state: bool = True,
    liquidate: bool = False,
) -> tuple[HyperdriveReadWriteInterface, list[HyperdriveAgent], EthConfig, HyperdriveAddresses]:
    """Entrypoint to setup agents for automated trading.

    Arguments
    ---------
    environment_config: EnvironmentConfig
        The agent's environment configuration.
    agent_config: list[AgentConfig]
        The list of agent configurations to run.
    account_key_config: AccountKeyConfig
        Dataclass containing configuration options for the agent account, including keys and budgets.
    eth_config: EthConfig | None, optional
        Configuration for URIs to the rpc and artifacts.
        If not set, will look for the config in eth.env.
    contract_addresses: HyperdriveAddresses | None, optional
        Configuration for the URIs to the Hyperdrive contract addresses.
        If not set, will look for the addresses in eth_config.
    load_wallet_state: bool, optional
        If set, will connect to the db api to load wallet states from the current chain.
        Defaults to True.
    liquidate: bool, optional
        If set, will ignore all policy settings and liquidate all open positions.
        Defaults to False.

    Returns
    -------
    tuple[HyperdriveReadWriteInterface, list[HyperdriveAgent], EthConfig, HyperdriveAddresses]
        A tuple containing:
            - The Hyperdrive interface API object
            - A list of HyperdriveAgent objects that contain a wallet address and Agent for determining trades
            - The eth_config with defaults assigned.
            - The contract_addresses with defaults assigned.
    """
    # See if develop flag is set
    develop_env = os.environ.get("DEVELOP")
    develop = (develop_env is not None) and (develop_env.lower() == "true")

    # Defaults to looking for eth_config env
    if eth_config is None:
        eth_config = build_eth_config()
    if contract_addresses is None:
        contract_addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))

    # create hyperdrive interface object
    interface = HyperdriveReadWriteInterface(
        eth_config,
        contract_addresses,
        read_retry_count=environment_config.read_retry_count,
        write_retry_count=environment_config.write_retry_count,
    )

    # Setup env automatically & fund the agents
    if develop:
        _ = async_fund_agents_with_fake_user(eth_config, account_key_config, contract_addresses, interface)

    # Get hyperdrive interface object and agents
    agent_accounts = setup_experiment(
        environment_config,
        agent_config,
        account_key_config,
        interface,
    )
    wallet_addrs = [str(agent.checksum_address) for agent in agent_accounts]

    # Set up database
    if not develop and eth_config.database_api_uri is not None:
        # Ignore this check if not develop
        if environment_config.username == DEFAULT_USERNAME:
            # Check for default name and exit if is default
            raise ValueError("Default username detected, please update 'username' in your environment config.")
        # Register wallet addresses to username
        register_username(eth_config.database_api_uri, wallet_addrs, environment_config.username)

    # Load existing balances
    if load_wallet_state:
        if eth_config.database_api_uri is not None:
            # Get existing open positions from db api server
            balances = balance_of(eth_config.database_api_uri, wallet_addrs)
            # Set balances of wallets based on db and chain
            for agent in agent_accounts:
                # TODO is this the right location for this to happen?
                # On one hand, doing it here makes sense because parameters such as db uri doesn't have to
                # be passed in down all the function calls when wallets are initialized.
                # On the other hand, we initialize empty wallets just to overwrite here.
                # Keeping here for now for later discussion
                agent.wallet = build_wallet_positions_from_data(
                    agent.checksum_address, balances, interface.base_token_contract
                )
        else:
            for agent in agent_accounts:
                agent.wallet = build_wallet_positions_from_chain(
                    agent.checksum_address, interface.hyperdrive_contract, interface.base_token_contract
                )

    # If we're in liquidation mode, we explicitly set halt on errors to false
    # This is due to an expected error when redeeming withdrawal shares
    if liquidate:
        environment_config.halt_on_errors = False
    return interface, agent_accounts, eth_config, contract_addresses


def run_agents(
    environment_config: EnvironmentConfig,
    eth_config: EthConfig,
    account_key_config: AccountKeyConfig,
    contract_addresses: HyperdriveAddresses,
    interface: HyperdriveReadWriteInterface,
    agent_accounts: list[HyperdriveAgent],
    liquidate: bool = False,
    minimum_avg_agent_base: FixedPoint | None = None,
):
    """Run agent trades in a forever (while True) loop.

    Arguments
    ---------
    environment_config: EnvironmentConfig
        The agent's environment configuration.
    eth_config: EthConfig
        Configuration for URIs to the rpc and artifacts.
    account_key_config: AccountKeyConfig
        Dataclass containing configuration options for the agent account, including keys and budgets.
    contract_addresses: HyperdriveAddresses | None, optional
        Configuration for the URIs to the Hyperdrive contract addresses.
        If not set, will look for the addresses in eth_config.
    interface: HyperdriveReadWriteInterface
        An interface for Hyperdrive with contracts deployed on any chain with an RPC url.
    agent_accounts: list[HyperdriveAgent]
        A list of HyperdriveAgent that are conducting the trades
    liquidate: bool, optional
        If set, will ignore all policy settings and liquidate all open positions.
        Defaults to False.
    minimum_avg_agent_base: FixedPoint, optional
        If set, then the script will fund the agents with their original budgets
        whenever the average balance across wallets is less than this amount.
    """
    # Check if all agents done trading
    # If so, exit cleanly
    # The done trading state variable gets set internally
    last_executed_block = BlockNumber(0)
    poll_latency = START_LATENCY + random.uniform(0, 1)
    while True:
        if all(agent.done_trading for agent in agent_accounts):
            break
        new_executed_block = trade_if_new_block(
            interface,
            agent_accounts,
            environment_config.halt_on_errors,
            environment_config.halt_on_slippage,
            environment_config.crash_report_to_file,
            environment_config.crash_report_file_prefix,
            environment_config.log_to_rollbar,
            last_executed_block,
            liquidate,
            environment_config.randomize_liquidation,
        )
        if minimum_avg_agent_base is not None:
            if (
                sum(agent.wallet.balance.amount for agent in agent_accounts) / FixedPoint(len(agent_accounts))
                < minimum_avg_agent_base
            ):
                _ = async_fund_agents_with_fake_user(eth_config, account_key_config, contract_addresses, interface)
                # Update agent accounts with new wallet balances
                for agent in agent_accounts:
                    # Contract call to get base balance
                    (_, base_amount) = interface.get_eth_base_balances(agent)
                    base_obj = Quantity(amount=base_amount, unit=TokenType.BASE)
                    agent.wallet.balance = base_obj
        if new_executed_block == last_executed_block:
            # wait
            time.sleep(poll_latency)
            poll_latency *= BACKOFF
            poll_latency += random.uniform(0, 1)
        else:
            # Reset backoff
            poll_latency = START_LATENCY + random.uniform(0, 1)


def async_fund_agents_with_fake_user(
    eth_config: EthConfig,
    account_key_config: AccountKeyConfig,
    contract_addresses: HyperdriveAddresses,
    interface: HyperdriveReadWriteInterface,
) -> HyperdriveAgent:
    """Create a fake account, fund it with eth, and then use that to fund the agent wallets.

    Arguments
    ---------
    eth_config: EthConfig | None, optional
        Configuration for URIs to the rpc and artifacts.
        If not set, will look for the config in eth.env.
    account_key_config: AccountKeyConfig
        Dataclass containing configuration options for the agent account, including keys and budgets.
    contract_addresses: HyperdriveAddresses | None, optional
        Configuration for the URIs to the Hyperdrive contract addresses.
        If not set, will look for the addresses in eth_config.
    interface: HyperdriveReadWriteInterface
        An interface for Hyperdrive with contracts deployed on any chain with an RPC url.

    Returns
    -------
    HyperdriveAgent
        The fake user account created to fund the agents.
    """
    user_account = create_and_fund_user_account(account_key_config, interface)
    asyncio.run(async_fund_agents(user_account, eth_config, account_key_config, contract_addresses))
    return user_account


def build_wallet_positions_from_data(
    wallet_addr: str, db_balances: pd.DataFrame, base_contract: ERC20MintableContract
) -> HyperdriveWallet:
    """Builds a wallet position based on gathered data.

    Arguments
    ---------
    wallet_addr: str
        The checksum wallet address
    db_balances: pd.DataFrame
        The current positions dataframe gathered from the db (from the `balance_of` api call)
    base_contract: Contract
        The base contract to query the base amount from

    Returns
    -------
    HyperdriveWallet
        The wallet object build from the provided data
    """
    # Contract call to get base balance
    base_amount: int = base_contract.functions.balanceOf(wallet_addr).call()
    # TODO do we need to do error checking here?
    base_obj = Quantity(amount=FixedPoint(scaled_value=base_amount), unit=TokenType.BASE)

    # TODO We can also get lp and withdraw shares from chain?
    wallet_balances = db_balances[db_balances["wallet_address"] == wallet_addr]

    # Get longs
    long_balances = wallet_balances[wallet_balances["base_token_type"] == "LONG"]
    long_obj = {}
    # Casting maturity_time to int due to values getting encoded as strings
    for _, row in long_balances.iterrows():
        maturity_time = int(row["maturity_time"])
        long_obj[maturity_time] = Long(balance=FixedPoint(row["value"]), maturity_time=maturity_time)

    short_balances = wallet_balances[wallet_balances["base_token_type"] == "SHORT"]
    short_obj = {}
    # Casting maturity_time to int due to values getting encoded as strings
    for _, row in short_balances.iterrows():
        maturity_time = int(row["maturity_time"])
        short_obj[maturity_time] = Short(balance=FixedPoint(row["value"]), maturity_time=maturity_time)

    lp_balances = wallet_balances[wallet_balances["base_token_type"] == "LP"]
    assert len(lp_balances) <= 1
    if len(lp_balances) == 0:
        lp_obj = FixedPoint(0)
    else:
        lp_obj = FixedPoint(lp_balances.iloc[0]["value"])

    withdraw_balances = wallet_balances[wallet_balances["base_token_type"] == "WITHDRAWAL_SHARE"]
    assert len(withdraw_balances) <= 1
    if len(withdraw_balances) == 0:
        withdraw_obj = FixedPoint(0)
    else:
        withdraw_obj = FixedPoint(withdraw_balances.iloc[0]["value"])

    return HyperdriveWallet(
        address=HexBytes(wallet_addr),
        balance=base_obj,
        lp_tokens=lp_obj,
        withdraw_shares=withdraw_obj,
        longs=long_obj,
        shorts=short_obj,
    )


def build_wallet_positions_from_chain(
    wallet_addr: str, hyperdrive_contract: IERC4626HyperdriveContract, base_contract: ERC20MintableContract
) -> HyperdriveWallet:
    """Builds a wallet position based on gathered data.

    Arguments
    ---------
    wallet_addr: str
        The checksum wallet address
    hyperdrive_contract: Contract
        The Hyperdrive contract to query the data from
    base_contract: Contract
        The base contract to query the base amount from

    Returns
    -------
    HyperdriveWallet
        The wallet object build from the provided data
    """
    # Contract call to get base balance
    base_amount: int = base_contract.functions.balanceOf(wallet_addr).call()
    # TODO do we need to do error checking here?
    base_obj = Quantity(amount=FixedPoint(scaled_value=base_amount), unit=TokenType.BASE)

    # Contract call to get lp balance
    asset_id = encode_asset_id(AssetIdPrefix.LP, 0)
    lp_amount: int = hyperdrive_contract.functions.balanceOf(asset_id, wallet_addr).call()
    lp_obj = FixedPoint(scaled_value=lp_amount)

    # Contract call to get withdrawal positions
    asset_id = encode_asset_id(AssetIdPrefix.WITHDRAWAL_SHARE, 0)
    withdraw_amount: int = hyperdrive_contract.functions.balanceOf(asset_id, wallet_addr).call()
    withdraw_obj = FixedPoint(scaled_value=withdraw_amount)

    # We need to gather all longs and shorts from events
    # and rebuild the current long/short positions
    # Open Longs
    open_long_events = hyperdrive_contract.events.OpenLong.get_logs(fromBlock=0)
    long_obj: dict[int, Long] = {}
    for event in open_long_events:
        maturity_time = event["args"]["maturityTime"]
        long_amount = FixedPoint(scaled_value=event["args"]["bondAmount"])
        # Add this balance to the wallet if it exists, create the long object if not
        if maturity_time in long_obj:
            long_obj[maturity_time].balance += long_amount
        else:
            long_obj[maturity_time] = Long(balance=long_amount, maturity_time=maturity_time)
    # Close Longs
    close_long_events = hyperdrive_contract.events.CloseLong.get_logs(fromBlock=0)
    for event in close_long_events:
        maturity_time = event["args"]["maturityTime"]
        long_amount = FixedPoint(scaled_value=event["args"]["bondAmount"])
        assert maturity_time in long_obj
        long_obj[maturity_time].balance -= long_amount
    # Iterate through longs and remove any zero balance
    for k in list(long_obj.keys()):
        # Sanity check
        assert long_obj[k].balance >= FixedPoint(0)
        if long_obj[k].balance == FixedPoint(0):
            del long_obj[k]

    # Open Shorts
    open_short_events = hyperdrive_contract.events.OpenShort.get_logs(fromBlock=0)
    short_obj: dict[int, Short] = {}
    for event in open_short_events:
        maturity_time = event["args"]["maturityTime"]
        short_amount = FixedPoint(scaled_value=event["args"]["bondAmount"])
        # Add this balance to the wallet if it exists, create the short object if not
        if maturity_time in short_obj:
            short_obj[maturity_time].balance += short_amount
        else:
            short_obj[maturity_time] = Short(balance=short_amount, maturity_time=maturity_time)
    # Close Shorts
    close_short_events = hyperdrive_contract.events.CloseShort.get_logs(fromBlock=0)
    for event in close_short_events:
        maturity_time = event["args"]["maturityTime"]
        short_amount = FixedPoint(scaled_value=event["args"]["bondAmount"])
        assert maturity_time in short_obj
        short_obj[maturity_time].balance -= short_amount
    # Iterate through longs and remove any zero balance
    for k in list(short_obj.keys()):
        # Sanity check
        assert short_obj[k].balance >= FixedPoint(0)
        if short_obj[k].balance == FixedPoint(0):
            del short_obj[k]

    return HyperdriveWallet(
        address=HexBytes(wallet_addr),
        balance=base_obj,
        lp_tokens=lp_obj,
        withdraw_shares=withdraw_obj,
        longs=long_obj,
        shorts=short_obj,
    )
