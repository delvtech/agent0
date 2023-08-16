"""Runner script for bots"""
from __future__ import annotations

import logging
import os
import warnings

from agent0 import AccountKeyConfig
from agent0.base.config import DEFAULT_USERNAME, AgentConfig, EnvironmentConfig
from eth_typing import BlockNumber
from ethpy import EthConfig, build_eth_config
from ethpy.hyperdrive.addresses import HyperdriveAddresses, fetch_hyperdrive_address_from_url

from .create_and_fund_accounts import create_and_fund_user_account
from .fund_bots import fund_bots
from .setup_experiment import register_username, setup_experiment
from .trade_loop import trade_if_new_block


# TODO consolidate various configs into one config?
# Unsure if above is necessary, as long as key agent0 interface is concise.
# pylint: disable=too-many-arguments
def run_bots(
    environment_config: EnvironmentConfig,
    agent_config: list[AgentConfig],
    account_key_config: AccountKeyConfig,
    develop: bool = False,
    eth_config: EthConfig | None = None,
    override_addresses: HyperdriveAddresses | None = None,
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
        Configuration for urls to the rpc and artifacts. If not set, will look for addresses
        in eth.env.
    override_addresses: HyperdriveAddresses | None
        If set, will use these addresses instead of querying the artifact url
        defined in eth_config.
    """

    # Defaults to looking for eth_config env
    if eth_config is None:
        eth_config = build_eth_config()

    # Set sane logging defaults to avoid spam from dependencies
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("web3").setLevel(logging.WARNING)
    warnings.filterwarnings("ignore", category=UserWarning, module="web3.contract.base_contract")

    # Get addresses either from artifacts url defined in eth_config or from override_addresses
    if override_addresses is not None:
        contract_addresses = override_addresses
    else:
        contract_addresses = fetch_hyperdrive_address_from_url(os.path.join(eth_config.ARTIFACTS_URL, "addresses.json"))

    if develop:  # setup env automatically & fund the bots
        # exposing the user account for debugging purposes
        user_account = create_and_fund_user_account(eth_config, account_key_config, contract_addresses)
        fund_bots(
            user_account, eth_config, account_key_config, contract_addresses
        )  # uses env variables created above as inputs

    web3, _, hyperdrive_contract, agent_accounts = setup_experiment(
        eth_config, environment_config, agent_config, account_key_config, contract_addresses
    )

    if not develop:
        if environment_config.username == DEFAULT_USERNAME:
            # Check for default name and exit if is default
            raise ValueError(
                "Default username detected, please update 'username' in "
                "lib/agent0/agent0/hyperdrive/config/runner_config.py"
            )
        # Set up postgres to write username to agent wallet addr
        # initialize the postgres session
        wallet_addrs = [str(agent.checksum_address) for agent in agent_accounts]
        register_username(environment_config.username_register_url, wallet_addrs, environment_config.username)

    last_executed_block = BlockNumber(0)
    while True:
        last_executed_block = trade_if_new_block(
            web3,
            hyperdrive_contract,
            agent_accounts,
            environment_config.halt_on_errors,
            last_executed_block,
        )
