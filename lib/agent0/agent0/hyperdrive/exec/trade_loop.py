"""Helper function for executing a set of trades"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

from agent0.hyperdrive.agents import HyperdriveAgent
from agent0.hyperdrive.crash_report import get_anvil_state_dump, log_hyperdrive_crash_report
from agent0.hyperdrive.state import HyperdriveActionType, TradeResult, TradeStatus
from ethpy.base.errors import ContractCallException
from ethpy.hyperdrive import HyperdriveInterface
from web3 import Web3
from web3.exceptions import ContractCustomError, ContractLogicError
from web3.types import RPCEndpoint

from .execute_agent_trades import assert_never, async_execute_agent_trades

# TODO: Suppress logging from ethpy here as agent0 handles logging


# TODO cleanup this function
# pylint: disable=too-many-arguments
def trade_if_new_block(
    hyperdrive: HyperdriveInterface,
    agent_accounts: list[HyperdriveAgent],
    halt_on_errors: bool,
    halt_on_slippage: bool,
    crash_report_to_file: bool,
    last_executed_block: int,
    liquidate: bool,
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
    liquidate: bool
        If set, will ignore all policy settings and liquidate all open positions

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
            "Block number: %d, Block time: %s, Price: %s, Rate: %s",
            latest_block_number,
            str(datetime.fromtimestamp(float(latest_block_timestamp))),
            hyperdrive.spot_price,
            hyperdrive.fixed_rate,
        )
        # To avoid jumbled print statements due to asyncio, we handle all logging and crash reporting
        # here, with inner functions returning trade results.
        trade_results: list[TradeResult] = asyncio.run(
            async_execute_agent_trades(hyperdrive, agent_accounts, liquidate)
        )
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
                # Here, we check for common errors and allow for custom handling of various errors

                # These functions adjust the trade_result.exception object to add
                # additional arguments describing these detected errors for crash reporting
                # These functions also return a boolean to determine if they detected
                # these issues
                _, trade_result = check_for_invalid_balance(trade_result)
                is_slippage, trade_result = check_for_slippage(trade_result)

                # Sanity check: exception should not be none if trade failed
                # Additionally, crash reporting information should exist
                assert trade_result.exception is not None
                assert trade_result.pool_config is not None
                assert trade_result.pool_info is not None

                # Crash reporting
                if is_slippage:
                    log_hyperdrive_crash_report(trade_result, logging.WARNING, crash_report_to_file=False)
                else:
                    # We only get anvil state dump here, since it's an on chain call
                    # and we don't want to do it when e.g., slippage happens
                    if crash_report_to_file:
                        trade_result.anvil_state = get_anvil_state_dump(hyperdrive.web3)
                    # Defaults to CRITICAL
                    log_hyperdrive_crash_report(trade_result, crash_report_to_file=crash_report_to_file)

                if halt_on_errors:
                    # Don't halt if slippage detected and halt_on_slippage is false
                    if not is_slippage or halt_on_slippage:
                        raise trade_result.exception
            else:
                # Should never get here
                assert False
    return last_executed_block


def check_for_slippage(trade_result) -> tuple[bool, TradeResult]:
    """Detects slippage errors in trade_result and adds additional information to the
    exception in trade_result

    Arguments
    ---------
    trade_result: TradeResult
        The trade result object from trading

    Returns
    -------
    tuple(bool, TradeResult)
        A tuple of a flag for detecting slippage and
        a modified trade_result that has a custom exception argument message prepended
    """
    # To detect slippage, we first look for the wrapper that defines a contract call exception.
    # We then look for the `OutputLimit` exception thrown as the original exception.
    # Since this exception is used elsewhere (e.g., in redeem withdraw shares), we also explicitly check
    # that the trade here is open/close long/short.
    # TODO this error is not guaranteed to be exclusive for slippage in the future.
    is_slippage = (
        isinstance(trade_result.exception, ContractCallException)
        and isinstance(trade_result.exception.orig_exception, ContractCustomError)
        and ("OutputLimit raised" in trade_result.exception.orig_exception.args[1])
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
        # Prepend slippage argument to exception args
        trade_result.exception.args = ("Slippage detected",) + trade_result.exception.args

    return is_slippage, trade_result


def check_for_invalid_balance(trade_result: TradeResult) -> tuple[bool, TradeResult]:
    """Detects invalid balance errors in trade_result and adds additional information to the
    exception in trade_result

    Arguments
    ---------
    trade_result: TradeResult
        The trade result object from trading

    Returns
    -------
    tuple(bool, TradeResult)
        A tuple of a flag for detecting invalid balance and
        a modified trade_result that has a custom exception argument message prepended
    """

    wallet = trade_result.agent.wallet
    trade_type = trade_result.trade_object.market_action.action_type
    trade_amount = trade_result.trade_object.market_action.trade_amount
    maturity_time = trade_result.trade_object.market_action.maturity_time
    invalid_balance = False
    add_arg = None
    match trade_type:
        case HyperdriveActionType.INITIALIZE_MARKET:
            raise ValueError(f"{trade_type} not supported!")

        case HyperdriveActionType.OPEN_LONG:
            if trade_amount > wallet.balance.amount:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} {wallet.balance.unit.name}, "
                    f"balance of {wallet.balance.amount} {wallet.balance.unit.name}."
                )

        case HyperdriveActionType.CLOSE_LONG:
            # Long doesn't exist
            if maturity_time not in wallet.longs:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} long-{maturity_time}, "
                    f"long token not found in wallet."
                )
            # Long exists but not enough balance
            else:
                invalid_balance = True
                if trade_amount > wallet.longs[maturity_time].balance:
                    add_arg = (
                        f"Invalid balance: {trade_type.name} for {trade_amount} long-{maturity_time}, "
                        f"balance of {wallet.longs[maturity_time].balance} long-{maturity_time}."
                    )

        case HyperdriveActionType.OPEN_SHORT:
            # We can't check for invalid balance here since the trade_amount is in units of bonds, and the
            # amount of base needed for the short isn't available. However, the exception itself has the
            # "ERC20: transfer amount exceeds balance" error, so should be okay.
            # TODO this should be solvable using some sort of preview, but the above error might be sufficient.

            # We explicitly check for the error here to set flag
            # TODO this catch is not guaranteed to be correct in the future.
            if (
                isinstance(trade_result.exception, ContractCallException)
                and isinstance(trade_result.exception.orig_exception, ContractLogicError)
                and ("ERC20: transfer amount exceeds balance" in trade_result.exception.args[0])
            ):
                invalid_balance = True

        case HyperdriveActionType.CLOSE_SHORT:
            # Short doesn't exist
            if maturity_time not in wallet.shorts:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} short-{maturity_time}, "
                    f"short token not found in wallet."
                )
            # Short exists but not enough balance
            else:
                if trade_amount > wallet.shorts[maturity_time].balance:
                    invalid_balance = True
                    add_arg = (
                        f"Invalid balance: {trade_type.name} for {trade_amount} short-{maturity_time}, "
                        f"balance of {wallet.shorts[maturity_time].balance} short-{maturity_time}."
                    )

        case HyperdriveActionType.ADD_LIQUIDITY:
            if trade_amount > wallet.balance.amount:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} {wallet.balance.unit.name}, "
                    f"balance of {wallet.balance.amount} {wallet.balance.unit.name}."
                )

        case HyperdriveActionType.REMOVE_LIQUIDITY:
            if trade_amount > wallet.lp_tokens:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} LP tokens, "
                    f"balance of {wallet.lp_tokens} LP tokens."
                )

        case HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
            # If we're crash reporting, pool_info should exist
            assert trade_result.pool_info is not None
            ready_to_withdraw = trade_result.pool_info["withdrawalSharesReadyToWithdraw"]
            if trade_amount > wallet.withdraw_shares:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} withdraw shares, "
                    f"balance of {wallet.withdraw_shares} withdraw shares."
                )
            # Also checking that there are enough withdrawal shares ready to withdraw
            elif trade_amount > ready_to_withdraw:
                # This isn't really an invalid balance error, so we won't set the flag here
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} withdraw shares, "
                    f"not enough ready to withdraw shares in pool ({ready_to_withdraw})."
                )

        case _:
            assert_never(trade_type)

    assert trade_result.exception is not None
    # Prepend balance error argument to exception args
    if add_arg is not None:
        trade_result.exception.args = (add_arg,) + trade_result.exception.args
    return invalid_balance, trade_result


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
