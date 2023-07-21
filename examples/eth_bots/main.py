"""Main script for running bots on Hyperdrive"""
from __future__ import annotations

import logging
from datetime import datetime

from eth_typing import BlockNumber
from web3 import Web3
from web3.types import RPCEndpoint

# FIXME: Move configs into a dedicated config folder
from examples.eth_bots.config import agent_config, environment_config
from examples.eth_bots.execute_agent_trades import execute_agent_trades
from examples.eth_bots.setup_agents import get_agent_accounts
from examples.eth_bots.setup_experiment import setup_experiment


def main():  # FIXME: Move much of this out of main
    """Entrypoint to load all configurations and run agents."""
    rng, web3, base_token_contract, hyperdrive_contract = setup_experiment(environment_config)
    # load agent policies
    agent_accounts = get_agent_accounts(
        agent_config, environment_config, web3, base_token_contract, hyperdrive_contract.address, rng
    )

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
