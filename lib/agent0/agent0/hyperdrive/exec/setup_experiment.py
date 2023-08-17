"""Setup helper function for running eth agent experiments."""
from __future__ import annotations

from http import HTTPStatus

import numpy as np
import requests
from agent0 import AccountKeyConfig
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.agents import HyperdriveAgent
from agent0.hyperdrive.exec.crash_report import setup_hyperdrive_crash_report_logging
from elfpy.utils import logs
from ethpy import EthConfig
from ethpy.hyperdrive import HyperdriveAddresses, get_web3_and_hyperdrive_contracts
from web3 import Web3
from web3.contract.contract import Contract

from .get_agent_accounts import get_agent_accounts


def setup_experiment(
    eth_config: EthConfig,
    environment_config: EnvironmentConfig,
    agent_config: list[AgentConfig],
    account_key_config: AccountKeyConfig,
    contract_addresses: HyperdriveAddresses,
) -> tuple[Web3, Contract, Contract, list[HyperdriveAgent]]:
    """Get agents according to provided config, provide eth, base token and approve hyperdrive.

    Arguments
    ---------
    eth_config: EthConfig
        Configuration for urls to the rpc and artifacts.
    environment_config: EnvironmentConfig
        The agent's environment configuration.
    agent_config: list[AgentConfig]
        The list of agent configurations.
    account_key_config: AccountKeyConfig
        Configuration linking to the env file for storing private keys and initial budgets.
    contract_addresses: HyperdriveAddresses
        Configuration for defining various contract addresses.

    Returns
    -------
    tuple[Web3, Contract, Contract, EnvironmentConfig, list[HyperdriveAgent]]
        A tuple containing:
            - The web3 container
            - The base token contract
            - The hyperdrive contract
            - A list of HyperdriveAgent objects that contain a wallet address and Elfpy Agent for determining trades
    """

    # this random number generator should be used everywhere so that the experiment is repeatable
    # rng stores the state of the random number generator, so that we can pause and restart experiments from any point
    rng = np.random.default_rng(environment_config.random_seed)

    # setup logging
    logs.setup_logging(
        log_filename=environment_config.log_filename,
        max_bytes=environment_config.max_bytes,
        log_level=environment_config.log_level,
        delete_previous_logs=environment_config.delete_previous_logs,
        log_stdout=environment_config.log_stdout,
        log_format_string=environment_config.log_formatter,
    )
    setup_hyperdrive_crash_report_logging()
    web3, base_token_contract, hyperdrive_contract = get_web3_and_hyperdrive_contracts(eth_config, contract_addresses)
    # load agent policies
    # rng is shared by the agents and can be accessed via `agent_accounts[idx].policy.rng`
    agent_accounts = get_agent_accounts(
        web3, agent_config, account_key_config, base_token_contract, hyperdrive_contract.address, rng
    )
    return web3, base_token_contract, hyperdrive_contract, agent_accounts


def register_username(register_url: str, wallet_addrs: list[str], username: str) -> None:
    """Registers the username with the flask server.

    Arguments
    ---------
    register_url: str
        The endpoint for the flask server.
    wallet_addrs: list[str]
        The list of wallet addresses to register.
    username: str
        The username to register the wallet addresses under.
    """
    # TODO: use the json schema from the server.
    json_data = {"wallet_addrs": wallet_addrs, "username": username}
    result = requests.post(f"{register_url}/register_agents", json=json_data, timeout=3)
    if result.status_code != HTTPStatus.OK:
        raise ConnectionError(result)
