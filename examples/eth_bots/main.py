"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import logging
import os
from datetime import datetime

import numpy as np
import requests
from eth_typing import BlockNumber
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import RPCEndpoint

from elfpy import eth, hyperdrive_interface
from elfpy.bots import DEFAULT_USERNAME
from elfpy.utils import logs

# FIXME: Move configs into a dedicated config folder
from examples.eth_bots.config import agent_config, environment_config
from examples.eth_bots.execute_agent_trades import execute_agent_trades
from examples.eth_bots.setup_agents import get_agent_accounts


# FIXME: move this out of this file (into `elfpy/bots/register_username_server.py`?
def register_username(register_url: str, wallet_addrs: list[str], username):
    """Connects to the register user flask server via post request and registeres the username"""
    json_data = {"wallet_addrs": wallet_addrs, "username": username}
    result = requests.post(register_url + "/register_bots", json=json_data, timeout=3)
    if result.status_code != 200:
        raise ConnectionError(result)


def main():  # FIXME: Move much of this out of main
    """Entrypoint to load all configurations and run agents."""

    # TODO: all contract initialization should get encapsulated into something like 'setup_experiment()'
    ###################################
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

    # FIXME: move into get_agent_accounts
    # Set up postgres to write username to agent wallet addr
    # initialize the postgres session
    wallet_addrs = [str(agent.checksum_address) for agent in agent_accounts]
    register_username(environment_config.username_register_url, wallet_addrs, environment_config.username)

    # FIXME: encapulate trade loop to another function.  At most should be:
    # while: True:
    #    run_trades(...)
    # Run trade loop forever
    trade_streak = 0
    last_executed_block = BlockNumber(0)

    while True:
        latest_block = web3.eth.get_block("latest")
        latest_block_number = latest_block.get("number", None)
        latest_block_timestamp = latest_block.get("timestamp", None)
        if latest_block_number is None or latest_block_timestamp is None:
            raise AssertionError("latest_block_number and latest_block_timestamp can not be None")

        wait_for_new_block = get_wait_for_new_block(web3)
        print(f"{wait_for_new_block=}")

        # do trades if we don't need to wait for new block.  otherwise, wait and check for a new block
        if not wait_for_new_block or latest_block_number > last_executed_block:
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
            # we want to catch all exceptions
            # pylint: disable=broad-exception-caught
            except Exception as exc:
                if environment_config.halt_on_errors:
                    raise exc
                trade_streak = 0
                # FIXME: deliver crash report


# FIXME: improve this function name; move into eth/rpc_interface
def get_wait_for_new_block(web3: Web3) -> bool:
    """Returns if we should wait for a new block before attempting trades again.  For anvil nodes,
       if auto-mining is enabled then every transaction sent to the block is automatically mined so
       we don't need to wait for a new block before submitting trades again.

    Arguments
    ---------
    web3 : Web3
        web3.py instantiation.

    Returns
    -------
    bool
        Whether or not to wait for a new block before attempting trades again.
    """
    automine = False
    try:
        response = web3.provider.make_request(method=RPCEndpoint("anvil_getAutomine"), params=[])
        automine = bool(response.get("result", False))
    except Exception:  # pylint: disable=broad-exception-caught
        # do nothing, this will fail for non anvil nodes and we don't care.
        automine = False
    return not automine


if __name__ == "__main__":
    # Get postgres env variables if exists

    main()
