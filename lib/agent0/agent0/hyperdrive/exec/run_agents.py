"""Runner script for agents"""
from __future__ import annotations

import asyncio
import logging
import os
import random
import time
import warnings

import pandas as pd
from agent0 import AccountKeyConfig
from agent0.base import Quantity, TokenType
from agent0.base.config import DEFAULT_USERNAME, AgentConfig, EnvironmentConfig
from agent0.hyperdrive.state import HyperdriveWallet, Long, Short
from chainsync.db.api import balance_of, register_username
from eth_typing import BlockNumber
from ethpy import EthConfig, build_eth_config
from ethpy.base import smart_contract_read
from ethpy.hyperdrive import HyperdriveAddresses, fetch_hyperdrive_address_from_uri
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3.contract.contract import Contract

from .create_and_fund_user_account import create_and_fund_user_account
from .fund_agents import async_fund_agents
from .setup_experiment import setup_experiment
from .trade_loop import trade_if_new_block

START_LATENCY = 1
BACKOFF = 2


# TODO consolidate various configs into one config?
# Unsure if above is necessary, as long as key agent0 interface is concise.
# pylint: disable=too-many-arguments
# pylint: disable=too-many-locals
def run_agents(
    environment_config: EnvironmentConfig,
    agent_config: list[AgentConfig],
    account_key_config: AccountKeyConfig,
    eth_config: EthConfig | None = None,
    contract_addresses: HyperdriveAddresses | None = None,
    load_wallet_state: bool = True,
    liquidate: bool = False,
) -> None:
    """Entrypoint to run agents.

    Arguments
    ---------
    environment_config: EnvironmentConfig
        The agent's environment configuration.
    agent_config: list[AgentConfig]
        The list of agent configurations to run.
    account_key_config: AccountKeyConfig
        Configuration linking to the env file for storing private keys and initial budgets.
    develop: bool
        Flag for development mode.
    eth_config: EthConfig | None
        Configuration for URIs to the rpc and artifacts. If not set, will look for addresses
        in eth.env.
    contract_addresses: HyperdriveAddresses | None
        If set, will use these addresses instead of querying the artifact URI
        defined in eth_config.
    load_wallet_state: bool
        If set, will connect to the db api to load wallet states from the current chain
    liquidate: bool
        If set, will ignore all policy settings and liquidate all open positions
    """
    # See if develop flag is set
    develop_env = os.environ.get("DEVELOP")
    develop = (develop_env is not None) and (develop_env.lower() == "true")

    # set sane logging defaults to avoid spam from dependencies
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("web3").setLevel(logging.WARNING)
    warnings.filterwarnings("ignore", category=UserWarning, module="web3.contract.base_contract")
    # defaults to looking for eth_config env
    if eth_config is None:
        eth_config = build_eth_config()
    if contract_addresses is None:
        contract_addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))
    # setup env automatically & fund the agents
    if develop:
        # exposing the user account for debugging purposes
        user_account = create_and_fund_user_account(eth_config, account_key_config, contract_addresses)
        asyncio.run(
            async_fund_agents(user_account, eth_config, account_key_config, contract_addresses)
        )  # uses env variables created above as inputs
    # get hyperdrive interface object and agents
    hyperdrive, agent_accounts = setup_experiment(
        eth_config, environment_config, agent_config, account_key_config, contract_addresses
    )
    wallet_addrs = [str(agent.checksum_address) for agent in agent_accounts]
    # set up database
    if not develop:
        # Ignore this check if not develop
        if environment_config.username == DEFAULT_USERNAME:
            # Check for default name and exit if is default
            raise ValueError("Default username detected, please update 'username' in your environment config.")
        # Register wallet addresses to username
        register_username(eth_config.database_api_uri, wallet_addrs, environment_config.username)

    if load_wallet_state:
        # Load existing balances
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
                agent.checksum_address, balances, hyperdrive.base_token_contract
            )

    # If we're in liquidation mode, we explicitly set halt on errors to false
    # This is due to an expected error when redeeming withdrawal shares
    if liquidate:
        environment_config.halt_on_errors = False

    # run the trades
    last_executed_block = BlockNumber(0)
    poll_latency = START_LATENCY + random.uniform(0, 1)
    while True:
        # Check if all agents done trading
        # If so, exit cleanly
        # The done trading state variable gets set internally
        if all(agent.done_trading for agent in agent_accounts):
            break

        new_executed_block = trade_if_new_block(
            hyperdrive,
            agent_accounts,
            environment_config.halt_on_errors,
            environment_config.halt_on_slippage,
            last_executed_block,
            liquidate,
        )
        if new_executed_block == last_executed_block:
            # wait
            time.sleep(poll_latency)
            poll_latency *= BACKOFF
            poll_latency += random.uniform(0, 1)
        else:
            # Reset backoff
            poll_latency = START_LATENCY + random.uniform(0, 1)
        last_executed_block = new_executed_block


def build_wallet_positions_from_data(
    wallet_addr: str, db_balances: pd.DataFrame, base_contract: Contract
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
    base_amount: dict[str, int] = smart_contract_read(base_contract, "balanceOf", wallet_addr)
    # TODO do we need to do error checking here?
    assert "value" in base_amount
    base_obj = Quantity(amount=FixedPoint(scaled_value=base_amount["value"]), unit=TokenType.BASE)

    # TODO We can also get lp and withdraw shares from chain?
    wallet_balances = db_balances[db_balances["walletAddress"] == wallet_addr]

    # Get longs
    long_balances = wallet_balances[wallet_balances["baseTokenType"] == "LONG"]
    long_obj = {}
    # Casting maturityTime to int due to values getting encoded as strings
    for _, row in long_balances.iterrows():
        long_obj[int(row["maturityTime"])] = Long(balance=FixedPoint(row["value"]))

    short_balances = wallet_balances[wallet_balances["baseTokenType"] == "SHORT"]
    short_obj = {}
    # Casting maturityTime to int due to values getting encoded as strings
    for _, row in short_balances.iterrows():
        short_obj[int(row["maturityTime"])] = Short(balance=FixedPoint(row["value"]))

    lp_balances = wallet_balances[wallet_balances["baseTokenType"] == "LP"]
    assert len(lp_balances) <= 1
    if len(lp_balances) == 0:
        lp_obj = FixedPoint(0)
    else:
        lp_obj = FixedPoint(lp_balances.iloc[0]["value"])

    withdraw_balances = wallet_balances[wallet_balances["baseTokenType"] == "WITHDRAWAL_SHARE"]
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
