"""Helper function for executing a set of trades"""
from __future__ import annotations

import logging
from datetime import datetime

from web3 import Web3
from web3.contract.contract import Contract

from elfpy import eth
from elfpy.eth.accounts import EthAccount
from examples.eth_bots.execute_agent_trades import execute_agent_trades


def trade_if_new_block(
    web3: Web3,
    hyperdrive_contract: Contract,
    agent_accounts: list[EthAccount],
    halt_on_errors: bool,
    last_executed_block: int,
) -> int:
    """Execute trades if there is a new block.

    Arguments
    ---------
    web3 : Web3
        Web3 provider object
    hyperdrive_contract : Contract
        The deployed hyperdrive contract
    agent_accounts : list[EthAccount]]
        A list of EthAccount objects that contain a wallet address and Elfpy Agent for determining trades
    halt_on_errors : bool
        If true, raise an exception if a trade reverts. Otherwise, log a warning and move on.
    last_executed_block : int
        The block number when a trade last happened

    Returns
    -------
    int
        The block number when a trade last happened
    """
    latest_block = web3.eth.get_block("latest")
    latest_block_number = latest_block.get("number", None)
    latest_block_timestamp = latest_block.get("timestamp", None)
    if latest_block_number is None or latest_block_timestamp is None:
        raise AssertionError("latest_block_number and latest_block_timestamp can not be None")
    wait_for_new_block = eth.get_wait_for_new_block(web3)
    # do trades if we don't need to wait for new block.  otherwise, wait and check for a new block
    if not wait_for_new_block or latest_block_number > last_executed_block:
        # log and show block info
        logging.info(
            "Block number: %d, Block time: %s",
            latest_block_number,
            str(datetime.fromtimestamp(float(latest_block_timestamp))),
        )
        try:
            execute_agent_trades(
                web3,
                hyperdrive_contract,
                agent_accounts,
            )
            last_executed_block = latest_block_number
        # we want to catch all exceptions
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            # FIXME: deliver crash report
            if halt_on_errors:
                raise exc
    return last_executed_block
