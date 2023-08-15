"""Setup helper function for running eth bot experiments."""
from __future__ import annotations

import os
from http import HTTPStatus

import numpy as np
import requests
from agent0.base.config import EnvironmentConfig
from agent0.hyperdrive.agents import HyperdriveAgent
from agent0.hyperdrive.config import get_default_agent_config, get_default_environment_config
from agent0.hyperdrive.crash_report import setup_hyperdrive_crash_report_logging
from agent0.hyperdrive.exec import get_agent_accounts
from elfpy.utils import logs
from ethpy import EthConfig, build_eth_config
from ethpy.base import initialize_web3_with_http_provider, load_all_abis
from ethpy.hyperdrive import fetch_hyperdrive_address_from_url
from web3 import Web3
from web3.contract.contract import Contract


def setup_experiment(
    environment_config=None, agent_config=None
) -> tuple[Web3, Contract, Contract, EnvironmentConfig, EthConfig, list[HyperdriveAgent]]:
    """Get agents according to provided config, provide eth, base token and approve hyperdrive.

    Returns
    -------
    tuple[Web3, Contract, Contract, EnvironmentConfig, list[HyperdriveAgent]]
        A tuple containing:
            - The web3 container
            - The base token contract
            - The hyperdrive contract
            - The environment configuration
            - A list of HyperdriveAgent objects that contain a wallet address and Elfpy Agent for determining trades
    """
    # Get url configs from environment
    eth_config = build_eth_config()
    # get the user defined config variables
    if environment_config is None:
        environment_config = get_default_environment_config()
    if agent_config is None:
        agent_config = get_default_agent_config()

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
    web3, base_token_contract, hyperdrive_contract = get_web3_and_contracts(environment_config, eth_config)
    # load agent policies
    # rng is shared by the agents and can be accessed via `agent_accounts[idx].policy.rng`
    agent_accounts = get_agent_accounts(agent_config, web3, base_token_contract, hyperdrive_contract.address, rng)
    return web3, base_token_contract, hyperdrive_contract, environment_config, eth_config, agent_accounts


def get_web3_and_contracts(
    environment_config: EnvironmentConfig, eth_config: EthConfig
) -> tuple[Web3, Contract, Contract]:
    """Get the web3 container and the ERC20Base and Hyperdrive contracts.

    Arguments
    ---------
    environment_config : EnvironmentConfig
        An instantiated environment config with the appropriate URLs set


    Returns
    -------
    tuple[Web3, Contract, Contract]
        A tuple containing:
            - The web3 container
            - The base token contract
            - The hyperdrive contract
    """
    # point to chain env
    web3 = initialize_web3_with_http_provider(eth_config.RPC_URL, reset_provider=False)
    # setup base contract interface
    abis = load_all_abis(eth_config.ABI_DIR)
    addresses = fetch_hyperdrive_address_from_url(os.path.join(eth_config.ARTIFACTS_URL, "addresses.json"))
    # set up the ERC20 contract for minting base tokens
    # TODO is there a better way to pass in base and hyperdrive abi?
    base_token_contract: Contract = web3.eth.contract(
        abi=abis[environment_config.base_abi], address=web3.to_checksum_address(addresses.base_token)
    )
    # set up hyperdrive contract
    hyperdrive_contract: Contract = web3.eth.contract(
        abi=abis[environment_config.hyperdrive_abi],
        address=web3.to_checksum_address(addresses.mock_hyperdrive),
    )
    return web3, base_token_contract, hyperdrive_contract


def register_username(register_url: str, wallet_addrs: list[str], username: str) -> None:
    """Registers the username with the flask server."""
    # TODO: use the json schema from the server.
    json_data = {"wallet_addrs": wallet_addrs, "username": username}
    result = requests.post(f"{register_url}/register_bots", json=json_data, timeout=3)
    if result.status_code != HTTPStatus.OK:
        raise ConnectionError(result)
