"""Helper function for executing a set of trades"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from web3 import Web3
from web3.types import RPCEndpoint

from agent0.core.hyperdrive import HyperdriveAgent, TradeResult, TradeStatus
from agent0.core.hyperdrive.crash_report import get_anvil_state_dump, log_hyperdrive_crash_report
from agent0.core.test_utils import assert_never
from agent0.ethpy.hyperdrive import HyperdriveReadInterface, HyperdriveReadWriteInterface

from .execute_agent_trades import async_execute_agent_trades

# TODO: Suppress logging from agent0.ethpy here as agent0 handles logging


# TODO cleanup this function
# pylint: disable=too-many-arguments
def trade_if_new_block(
    interface: HyperdriveReadWriteInterface,
    agent_accounts: list[HyperdriveAgent],
    halt_on_errors: bool,
    halt_on_slippage: bool,
    crash_report_to_file: bool,
    crash_report_file_prefix: str,
    log_to_rollbar: bool,
    last_executed_block: int,
    liquidate: bool,
    randomize_liquidation: bool,
) -> int:
    """Execute trades if there is a new block.

    Arguments
    ---------
    interface: HyperdriveReadWriteInterface
        The Hyperdrive API interface object.
    agent_accounts: list[HyperdriveAgent]]
        A list of HyperdriveAgent objects that contain a wallet address and Agent for determining trades.
    halt_on_errors: bool
        If true, raise an exception if a trade reverts.
        Otherwise, log a warning and move on.
    halt_on_slippage: bool
        If halt_on_errors is true and halt_on_slippage is false, don't raise an exception if slippage happens.
    crash_report_to_file: bool
        Whether or not to save the crash report to a file.
    crash_report_file_prefix: str
        The string prefix to prepend to crash reports
    log_to_rollbar: bool
        Whether or not to log to rollbar.
    last_executed_block: int
        The block number when a trade last happened.
    liquidate: bool
        If set, will ignore all policy settings and liquidate all open positions.
    randomize_liquidation: bool
        If set, will randomize the order of liquidation trades

    Returns
    -------
    int
        The block number when a trade last happened
    """
    latest_block = interface.web3.eth.get_block("latest")
    latest_block_number = latest_block.get("number", None)
    latest_block_timestamp = latest_block.get("timestamp", None)
    if latest_block_number is None or latest_block_timestamp is None:
        raise AssertionError("latest_block_number and latest_block_timestamp can not be None")
    wait_for_new_block = get_wait_for_new_block(interface.web3)
    # do trades if we don't need to wait for new block.  otherwise, wait and check for a new block
    if not wait_for_new_block or latest_block_number > last_executed_block:
        # log and show block info
        logging.info(
            "Block number: %d, Block time: %s, Price: %s, Rate: %s",
            latest_block_number,
            str(datetime.fromtimestamp(float(latest_block_timestamp))),
            interface.calc_spot_price(),
            interface.calc_fixed_rate(),
        )
        # To avoid jumbled print statements due to asyncio, we handle all logging and crash reporting
        # here, with inner functions returning trade results.
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(interface, agent_accounts, liquidate, randomize_liquidation)
        )
        last_executed_block = latest_block_number

        check_result(
            trade_results,
            interface,
            halt_on_errors,
            halt_on_slippage,
            crash_report_to_file,
            crash_report_file_prefix,
            log_to_rollbar,
        )
    return last_executed_block


def check_result(
    trade_results: list[TradeResult],
    interface: HyperdriveReadInterface,
    halt_on_errors: bool,
    halt_on_slippage: bool,
    crash_report_to_file: bool,
    crash_report_file_prefix: str,
    log_to_rollbar: bool,
) -> None:
    """Check and handle SUCCESS or FAILURE status from each trade_result.

    Arguments
    ---------
    trade_results: list[TradeResult]
        A list of TradeResult dataclasses, one for each trade made by the agent.
    interface: HyperdriveReadInterface
        The Hyperdrive API interface object.
    halt_on_errors: bool
        If true, raise an exception if a trade reverts.
        Otherwise, log a warning and move on.
    halt_on_slippage: bool
        If halt_on_errors is true and halt_on_slippage is false, don't raise an exception if slippage happens.
    crash_report_to_file: bool
        Whether or not to save the crash report to a file.
    crash_report_file_prefix: str
        The string prefix to prepend to crash reports
    log_to_rollbar: bool
        Whether or not to log to rollbar.
    """
    for trade_result in trade_results:
        match trade_result.status:
            # If successful, log the successful trade
            case TradeStatus.SUCCESS:
                assert trade_result.trade_object is not None
                assert trade_result.agent is not None
                logging.info(
                    "AGENT %s (%s) performed %s for %g",
                    str(trade_result.agent.checksum_address),
                    trade_result.agent.policy.__class__.__name__,
                    trade_result.trade_object.market_action.action_type,
                    float(trade_result.trade_object.market_action.trade_amount),
                )
            # Otherwise, optionally fail and create a crash report
            case TradeStatus.FAIL:
                # Sanity check: exception should not be none if trade failed
                # Additionally, crash reporting information should exist
                assert trade_result.exception is not None
                assert trade_result.pool_config is not None
                assert trade_result.pool_info is not None

                # Crash reporting
                if trade_result.is_slippage:
                    log_hyperdrive_crash_report(
                        trade_result, logging.WARNING, crash_report_to_file=False, log_to_rollbar=False
                    )
                else:
                    # We only get anvil state dump here, since it's an on chain call
                    # and we don't want to do it when e.g., slippage happens
                    if crash_report_to_file:
                        trade_result.anvil_state = get_anvil_state_dump(interface.web3)
                    # Defaults to CRITICAL
                    log_hyperdrive_crash_report(
                        trade_result,
                        crash_report_to_file=crash_report_to_file,
                        crash_report_file_prefix=crash_report_file_prefix,
                        log_to_rollbar=log_to_rollbar,
                    )

                if halt_on_errors:
                    # Don't halt if slippage detected and halt_on_slippage is false
                    if not trade_result.is_slippage or halt_on_slippage:
                        raise trade_result.exception
            case _:
                # Should never get here
                assert_never(trade_result.status)


def get_wait_for_new_block(web3: Web3) -> bool:
    """Returns if we should wait for a new block before attempting trades again.  For anvil nodes,
       if auto-mining is enabled then every transaction sent to the block is automatically mined so
       we don't need to wait for a new block before submitting trades again.

    Arguments
    ---------
    web3: Web3
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
