"""Runner script for agents"""
from __future__ import annotations

import logging
import os
import warnings

import pandas as pd
from agent0 import AccountKeyConfig
from agent0.base.config import DEFAULT_USERNAME, AgentConfig, EnvironmentConfig
from eth_typing import BlockNumber
from ethpy import EthConfig, build_eth_config
from ethpy.base import smart_contract_read
from ethpy.hyperdrive import HyperdriveAddresses, fetch_hyperdrive_address_from_uri
from web3.contract.contract import Contract

from .create_and_fund_user_account import create_and_fund_user_account
from .fund_agents import fund_agents
from .setup_experiment import balance_of, register_username, setup_experiment
from .trade_loop import trade_if_new_block


# TODO consolidate various configs into one config?
# Unsure if above is necessary, as long as key agent0 interface is concise.
# pylint: disable=too-many-arguments
def run_agents(
    environment_config: EnvironmentConfig,
    agent_config: list[AgentConfig],
    account_key_config: AccountKeyConfig,
    develop: bool = False,
    eth_config: EthConfig | None = None,
    contract_addresses: HyperdriveAddresses | None = None,
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
    """

    # Set sane logging defaults to avoid spam from dependencies
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("web3").setLevel(logging.WARNING)
    warnings.filterwarnings("ignore", category=UserWarning, module="web3.contract.base_contract")

    # Defaults to looking for eth_config env
    if eth_config is None:
        eth_config = build_eth_config()

    # Get addresses either from artifacts URI defined in eth_config or from contract_addresses
    if contract_addresses is None:
        contract_addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))

    if develop:  # setup env automatically & fund the agents
        # exposing the user account for debugging purposes
        user_account = create_and_fund_user_account(eth_config, account_key_config, contract_addresses)
        fund_agents(
            user_account, eth_config, account_key_config, contract_addresses
        )  # uses env variables created above as inputs

    web3, base_contract, hyperdrive_contract, agent_accounts = setup_experiment(
        eth_config, environment_config, agent_config, account_key_config, contract_addresses
    )

    wallet_addrs = [str(agent.checksum_address) for agent in agent_accounts]
    if not develop:
        # Ignore this check if not develop
        if environment_config.username == DEFAULT_USERNAME:
            # Check for default name and exit if is default
            raise ValueError(
                "Default username detected, please update 'username' in "
                "lib/agent0/agent0/hyperdrive/config/runner_config.py"
            )
        # Register wallet addresses to username
        register_username(environment_config.database_api_uri, wallet_addrs, environment_config.username)

    # Get existing open positions from db api server
    balances = balance_of(environment_config.database_api_uri, wallet_addrs)

    # TODO Set balances of wallets based on db
    for agent in agent_accounts:
        build_wallet_positions_from_data(agent.checksum_address, balances, base_contract)

    last_executed_block = BlockNumber(0)
    while True:
        last_executed_block = trade_if_new_block(
            web3,
            hyperdrive_contract,
            agent_accounts,
            environment_config.halt_on_errors,
            last_executed_block,
        )


def build_wallet_positions_from_data(wallet_addr: str, db_balances: pd.DataFrame, base_contract: Contract):
    # Contract call to get base balance
    base_amount = smart_contract_read(base_contract, "balanceOf", wallet_addr)
    # TODO build base object

    # TODO We can also get lp and withdraw shares from chain?
    wallet_balances = db_balances[db_balances["walletAddress"] == wallet_addr]

    # Get longs
    long_balances = wallet_balances[wallet_balances["baseTokenType" == "LONG"]]
    # TODO iterate through long balances and build wallet object

    short_balances = wallet_balances[wallet_balances["baseTokenType" == "SHORT"]]
    # TODO iterate through short balances and build wallet object

    lp_balances = wallet_balances[wallet_balances["baseTokenType" == "LP"]]
    assert len(lp_balances) <= 1
    # TODO Build LP balances object

    withdraw_balances = wallet_balances[wallet_balances["baseTokenType" == "WITHDRAWAL_SHARE"]]
    assert len(withdraw_balances) <= 1
    # TODO Build withdraw share object
