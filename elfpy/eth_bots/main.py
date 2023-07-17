"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import os

import numpy as np
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface
from elfpy.utils import logs

from .config import agent_config, environment_config
from .execute_agent_trades import execute_agent_trades
from .setup_agents import get_agents


def main(hyperdrive_abi, base_abi, build_folder):  # FIXME: Move much of this out of main
    """Entrypoint to load all configurations and run agents."""
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

    # point to chain env
    web3 = eth.web3_setup.initialize_web3_with_http_provider(environment_config.rpc_url, reset_provider=False)

    # setup base contract interface
    hyperdrive_abis = eth.abi.load_all_abis(build_folder)
    addresses = hyperdrive_interface.fetch_hyperdrive_address_from_url(
        os.path.join(environment_config.artifacts_url, "addresses.json")
    )

    # set up the ERC20 contract for minting base tokens
    base_token_contract: Contract = web3.eth.contract(abi=hyperdrive_abis[base_abi], address=addresses.base_token)

    # set up hyperdrive contract
    hyperdrive_contract: Contract = web3.eth.contract(
        abi=hyperdrive_abis[hyperdrive_abi],
        address=addresses.mock_hyperdrive,
    )

    # load agent policies
    agents = get_agents(agent_config, web3, base_token_contract, rng)

    # Run trade loop forever
    trade_streak = 0
    last_executed_block = 0
    while True:
        trade_streak, last_executed_block = execute_agent_trades(
            environment_config,
            web3,
            base_token_contract,
            hyperdrive_contract,
            agents,
            last_executed_block,
            trade_streak,
        )
        # FIXME: TODO: if provider.auto_mine is set then run the `mine` function


if __name__ == "__main__":
    HYPERDRIVE_ABI = "IHyperdrive"
    BASE_ABI = "ERC20Mintable"
    BUILD_FOLDER = "./hyperdrive_solidity/.build"
    main(HYPERDRIVE_ABI, BASE_ABI, BUILD_FOLDER)
