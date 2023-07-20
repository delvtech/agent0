"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import logging
import os
from datetime import datetime

import numpy as np
from dotenv import load_dotenv
from eth_typing import BlockNumber
from web3.contract.contract import Contract

from elfpy import eth, hyperdrive_interface
from elfpy.bots import DEFAULT_USERNAME
from elfpy.data import postgres
from elfpy.utils import logs
from examples.eth_bots.config import agent_config, environment_config
from examples.eth_bots.execute_agent_trades import execute_agent_trades
from examples.eth_bots.setup_agents import get_agent_accounts


def main():  # TODO: Move much of this out of main
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

    # Check for default name and exit if is default
    if environment_config.username == DEFAULT_USERNAME:
        raise ValueError("Default username detected, please update 'username' in config.py")

    # point to chain env
    web3 = eth.web3_setup.initialize_web3_with_http_provider(environment_config.rpc_url, reset_provider=False)

    # TODO: all contract initialization should get encapsulated into something like 'setup_contracts()'
    ###################################
    # setup base contract interface
    hyperdrive_abis = eth.abi.load_all_abis(environment_config.build_folder)
    addresses = hyperdrive_interface.fetch_hyperdrive_address_from_url(
        os.path.join(environment_config.artifacts_url, "addresses.json")
    )

    # set up the ERC20 contract for minting base tokens
    base_token_contract: Contract = web3.eth.contract(
        abi=hyperdrive_abis[environment_config.base_abi], address=web3.to_checksum_address(addresses.base_token)
    )

    # set up hyperdrive contract
    hyperdrive_contract: Contract = web3.eth.contract(
        abi=hyperdrive_abis[environment_config.hyperdrive_abi],
        address=web3.to_checksum_address(addresses.mock_hyperdrive),
    )
    ###################################

    # load agent policies
    agent_accounts = get_agent_accounts(agent_config, web3, base_token_contract, hyperdrive_contract.address, rng)

    # TODO: remove postgres from main.py, too low level.
    # Set up postgres to write username to agent wallet addr
    # initialize the postgres session
    wallet_addrs = [str(agent.checksum_address) for agent in agent_accounts]
    session = postgres.initialize_session()
    postgres.add_user_map(environment_config.username, wallet_addrs, session)
    postgres.close_session(session)

    # TODO: encapulate trade loop to another function.  At most should be:
    # while: True:
    #    run_trades_forever(...)
    # Run trade loop forever
    trade_streak = 0
    last_executed_block = BlockNumber(0)

    while True:
        latest_block = web3.eth.get_block("latest")
        latest_block_number = latest_block.get("number", None)
        latest_block_timestamp = latest_block.get("timestamp", None)
        if latest_block_number is None or latest_block_timestamp is None:
            raise AssertionError("latest_block_number and latest_block_timestamp can not be None")

        if latest_block_number > last_executed_block:
            # log and show block info
            logging.info(
                "Block number: %d, Block time: %s, Trades without crashing: %s",
                latest_block_number,
                str(datetime.fromtimestamp(float(latest_block_timestamp))),
                trade_streak,
            )
            try:
                trade_streak = execute_agent_trades(
                    web3,
                    hyperdrive_contract,
                    agent_accounts,
                    trade_streak,
                )
                last_executed_block = latest_block_number
                # TODO: if provider.auto_mine is set then run the `mine` function
            # we want to catch all exceptions
            # pylint: disable=broad-exception-caught
            except Exception as exc:
                if environment_config.halt_on_errors:
                    raise exc
                trade_streak = 0
                # TODO: deliver crash report


if __name__ == "__main__":
    # Get postgres env variables if exists
    load_dotenv()

    main()
