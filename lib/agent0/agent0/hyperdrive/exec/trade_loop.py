"""Helper function for executing a set of trades"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from agent0.hyperdrive.agents import HyperdriveAgent
from agent0.hyperdrive.crash_report import log_hyperdrive_crash_report
from agent0.hyperdrive.state import HyperdriveActionType, TradeResult, TradeStatus
from ethpy.hyperdrive import HyperdriveInterface
from web3 import Web3
from web3.exceptions import ContractCustomError
from web3.types import RPCEndpoint

from .execute_agent_trades import async_execute_agent_trades

# TODO: Suppress logging from ethpy here as agent0 handles logging


def trade_if_new_block(
    hyperdrive: HyperdriveInterface,
    agent_accounts: list[HyperdriveAgent],
    halt_on_errors: bool,
    halt_on_slippage: bool,
    last_executed_block: int,
) -> int:
    """Execute trades if there is a new block.

    Arguments
    ---------
    hyperdrive : HyperdriveInterface
        The Hyperdrive API interface object
    agent_accounts : list[HyperdriveAgent]]
        A list of HyperdriveAgent objects that contain a wallet address and Elfpy Agent for determining trades
    halt_on_errors : bool
        If true, raise an exception if a trade reverts. Otherwise, log a warning and move on.
    halt_on_slippage: bool
        If halt_on_errors is true and halt_on_slippage is false,
        don't raise an exception if slippage happens.
    last_executed_block : int
        The block number when a trade last happened

    Returns
    -------
    int
        The block number when a trade last happened
    """
    latest_block = hyperdrive.web3.eth.get_block("latest")
    latest_block_number = latest_block.get("number", None)
    latest_block_timestamp = latest_block.get("timestamp", None)
    if latest_block_number is None or latest_block_timestamp is None:
        raise AssertionError("latest_block_number and latest_block_timestamp can not be None")
    wait_for_new_block = get_wait_for_new_block(hyperdrive.web3)
    # do trades if we don't need to wait for new block.  otherwise, wait and check for a new block
    if not wait_for_new_block or latest_block_number > last_executed_block:
        # log and show block info
        logging.info(
            "Block number: %d, Block time: %s",
            latest_block_number,
            str(datetime.fromtimestamp(float(latest_block_timestamp))),
        )
        # To avoid jumbled print statements due to asyncio, we handle all logging and crash reporting
        # here, with inner functions returning trade results.
        trade_results: list[TradeResult] = asyncio.run(async_execute_agent_trades(hyperdrive, agent_accounts))
        last_executed_block = latest_block_number

        for trade_result in trade_results:
            # If successful, log the successful trade
            if trade_result.status == TradeStatus.SUCCESS:
                logging.info(
                    "AGENT %s (%s) performed %s for %g",
                    str(trade_result.agent.checksum_address),
                    trade_result.agent.policy.__class__.__name__,
                    trade_result.trade_object.market_action.action_type,
                    float(trade_result.trade_object.market_action.trade_amount),
                )
            elif trade_result.status == TradeStatus.FAIL:
                # To detect slippage, we look for the `OutputLimit` exception thrown from the smart contract.
                # Since this exception is used elsewhere (e.g., in redeem withdraw shares), we also explicitly check
                # that the trade here is open/close long/short.
                # TODO this error is not guaranteed to be exclusive for slippage in the future.
                is_slippage = (
                    isinstance(trade_result.exception, ContractCustomError)
                    and ("OutputLimit raised" in trade_result.exception.args[1])
                    and (
                        trade_result.trade_object.market_action.action_type
                        in (
                            HyperdriveActionType.OPEN_LONG,
                            HyperdriveActionType.CLOSE_LONG,
                            HyperdriveActionType.OPEN_SHORT,
                            HyperdriveActionType.CLOSE_SHORT,
                        )
                    )
                )

                if is_slippage:
                    logging.warning(
                        "AGENT %s (%s) attempted %s for %g\nSlippage detected: %s",
                        str(trade_result.agent.checksum_address),
                        trade_result.agent.policy.__class__.__name__,
                        trade_result.trade_object.market_action.action_type,
                        float(trade_result.trade_object.market_action.trade_amount),
                        trade_result.exception,
                    )
                else:
                    logging.error(
                        "AGENT %s (%s) attempted %s for %g\nCrashed with error: %s",
                        str(trade_result.agent.checksum_address),
                        trade_result.agent.policy.__class__.__name__,
                        trade_result.trade_object.market_action.action_type,
                        float(trade_result.trade_object.market_action.trade_amount),
                        trade_result.exception,
                    )

                # Sanity check: exception should not be none if trade failed
                # Additionally, crash reporting information should exist
                assert trade_result.exception is not None
                assert trade_result.pool_config is not None
                assert trade_result.pool_info is not None

                # Crash reporting
                log_hyperdrive_crash_report(trade_result)

                if halt_on_errors:
                    # Don't halt if slippage detected and halt_on_slippage is false
                    if not is_slippage or halt_on_slippage:
                        raise trade_result.exception
            else:
                # Should never get here
                assert False
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
