"""Helper function for executing a set of trades"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from agent0.core.hyperdrive import HyperdriveAgent, TradeResult, TradeStatus
from agent0.core.hyperdrive.crash_report import get_anvil_state_dump, log_hyperdrive_crash_report
from agent0.core.hyperdrive.interactive.exec import check_for_new_block
from agent0.core.test_utils import assert_never
from agent0.ethpy.hyperdrive import HyperdriveReadInterface, HyperdriveReadWriteInterface

from .execute_multi_agent_trades import async_execute_multi_agent_trades


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
    last_executed_block_number: int,
    liquidate: bool,
    randomize_liquidation: bool,
) -> int:
    """Execute trades if there is a new block.

    .. note::
    This function will soon be deprecated in favor of the IHyperdrive workflow

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
    last_executed_block_number: int
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
    new_block, latest_block = check_for_new_block(interface, last_executed_block_number)
    # do trades if we don't need to wait for new block.  otherwise, wait and check for a new block
    if new_block:
        # log and show block info
        logging.info(
            "Block number: %d, Block time: %s, Price: %s, Rate: %s",
            interface.get_block_number(latest_block),
            str(datetime.fromtimestamp(float(interface.get_block_timestamp(latest_block)))),
            interface.calc_spot_price(),
            interface.calc_fixed_rate(),
        )
        # To avoid jumbled print statements due to asyncio, we handle all logging and crash reporting
        # here, with inner functions returning trade results.
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_multi_agent_trades(interface, agent_accounts, liquidate, randomize_liquidation)
        )
        last_executed_block_number = interface.get_block_number(latest_block)

        _check_result(
            trade_results,
            interface,
            halt_on_errors,
            halt_on_slippage,
            crash_report_to_file,
            crash_report_file_prefix,
            log_to_rollbar,
        )
    return last_executed_block_number


def _check_result(
    trade_results: list[TradeResult],
    interface: HyperdriveReadInterface,
    halt_on_errors: bool,
    halt_on_slippage: bool,
    crash_report_to_file: bool,
    crash_report_file_prefix: str,
    log_to_rollbar: bool,
) -> None:
    """Check and handle SUCCESS or FAILURE status from each trade_result.

    .. note::
    This function will soon be deprecated in favor of the IHyperdrive workflow

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
