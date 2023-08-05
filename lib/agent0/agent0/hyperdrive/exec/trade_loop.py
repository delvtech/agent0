"""Helper function for executing a set of trades"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from agent0.base.accounts import EthAgent
from agent0.hyperdrive.exec import async_execute_agent_trades
from web3 import Web3
from web3.contract.contract import Contract
from web3.types import RPCEndpoint


def trade_if_new_block(
    web3: Web3,
    hyperdrive_contract: Contract,
    agent_accounts: list[EthAgent],
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
    agent_accounts : list[EthAgent]]
        A list of EthAgent objects that contain a wallet address and Elfpy Agent for determining trades
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
    wait_for_new_block = get_wait_for_new_block(web3)
    # do trades if we don't need to wait for new block.  otherwise, wait and check for a new block
    if not wait_for_new_block or latest_block_number > last_executed_block:
        # log and show block info
        logging.info(
            "Block number: %d, Block time: %s",
            latest_block_number,
            str(datetime.fromtimestamp(float(latest_block_timestamp))),
        )
        try:
            asyncio.run(
                async_execute_agent_trades(
                    web3,
                    hyperdrive_contract,
                    agent_accounts,
                )
            )
            last_executed_block = latest_block_number
        # we want to catch all exceptions
        # pylint: disable=broad-exception-caught
        except Exception as exc:
            logging.info("Trade crashed with error: %s", exc)
            # TODO: Crash reporting
            # We don't have all of the variables we need here -- this report needs to be generated at a lower level
            # logs.log_hyperdrive_crash_report(
            #     amount=trade_object.trade.trade_amount.scaled_value,
            #     trade_type=trade_object.trade.action_type,
            #     error=err,
            #     agent_address=agent.address,
            #     pool_info=pool_info,
            #     pool_config=pool_config,
            # )
            if halt_on_errors:
                raise exc
    return last_executed_block


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
