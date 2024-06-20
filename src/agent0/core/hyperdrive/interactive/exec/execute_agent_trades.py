"""Execute trades from agents and manage errors."""

from __future__ import annotations

import asyncio
import logging
from copy import deepcopy

from eth_account.signers.local import LocalAccount
from numpy.random import Generator
from web3.types import Nonce

from agent0.core.base import MarketType, Trade
from agent0.core.hyperdrive import HyperdriveActionType, HyperdriveMarketAction, HyperdriveWallet, TradeResult
from agent0.core.hyperdrive.agent import (
    close_long_trade,
    close_short_trade,
    redeem_withdraw_shares_trade,
    remove_liquidity_trade,
)
from agent0.core.hyperdrive.crash_report import (
    build_crash_trade_result,
    check_for_insufficient_allowance,
    check_for_invalid_balance,
    check_for_min_txn_amount,
    check_for_slippage,
)
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.core.test_utils import assert_never
from agent0.ethpy.base.transactions import DEFAULT_READ_RETRY_COUNT
from agent0.ethpy.hyperdrive import HyperdriveReadInterface, HyperdriveReadWriteInterface, ReceiptBreakdown
from agent0.utils import retry_call


def _get_liquidation_trades(
    interface: HyperdriveReadInterface, wallet: HyperdriveWallet, randomize_trades: bool, rng: Generator
) -> list[Trade[HyperdriveMarketAction]]:
    minimum_transaction_amount = interface.pool_config.minimum_transaction_amount
    action_list = []
    for maturity_time, long in wallet.longs.items():
        logging.debug("closing long: maturity_time=%g, balance=%s", maturity_time, long)
        if long.balance > minimum_transaction_amount:
            action_list.append(close_long_trade(long.balance, maturity_time))
    for maturity_time, short in wallet.shorts.items():
        logging.debug(
            "closing short: maturity_time=%g, balance=%s",
            maturity_time,
            short.balance,
        )
        if short.balance > minimum_transaction_amount:
            action_list.append(close_short_trade(short.balance, maturity_time))
    if wallet.lp_tokens > minimum_transaction_amount:
        logging.debug("closing lp: lp_tokens=%s", wallet.lp_tokens)
        action_list.append(remove_liquidity_trade(wallet.lp_tokens))

    # We use the underlying policies rng object for randomizing liquidation trades
    if randomize_trades:
        action_list = rng.permutation(action_list).tolist()

    # Always set withdrawal shares to be last, as we need trades to close first before withdrawing
    if wallet.withdraw_shares > 0:
        logging.debug("closing withdrawal: withdrawal_tokens=%s", wallet.withdraw_shares)
        action_list.append(redeem_withdraw_shares_trade(wallet.withdraw_shares))

    return action_list


def _get_trades(
    interface: HyperdriveReadInterface, policy: HyperdriveBasePolicy, wallet: HyperdriveWallet
) -> list[Trade[HyperdriveMarketAction]]:
    # TODO this function likely should live in policy

    # get the action list from the policy
    actions: list[Trade[HyperdriveMarketAction]] = []
    # Short circuit if the done_trading flag is set
    if not policy._done_trading:  # pylint: disable=protected-access
        actions, policy._done_trading = policy.action(interface, wallet)

    # Policy action checking
    for action in actions:
        if action.market_type == MarketType.HYPERDRIVE and action.market_action.maturity_time is None:
            if action.market_action.trade_amount <= 0:
                raise ValueError("Trade amount cannot be zero or negative.")

    return actions


# pylint: disable=too-many-arguments
async def async_execute_agent_trades(
    interface: HyperdriveReadWriteInterface,
    account: LocalAccount,
    wallet: HyperdriveWallet,
    policy: HyperdriveBasePolicy | None,
    preview_before_trade: bool,
    liquidate: bool,
    randomize_liquidation: bool = False,
    rng: Generator | None = None,
) -> list[TradeResult]:
    """Executes a single agent's trade based on its policy.
    This function is async as `_match_contract_call_to_trade` waits for a transaction receipt.

    .. note :: This function is not thread safe, as
    (1) the agent's policies `action` and `post_action` may not be thread safe, and
    (2) the agent's wallet update is not thread safe.
    (3) acquiring the base nonce for this set of trades is not thread safe.

    Arguments
    ---------
    interface: HyperdriveReadWriteInterface
        The Hyperdrive API interface object.
    account: LocalAccount
        The account that is conducting the trade.
    wallet: HyperdriveWallet
        The agent wallet object tied to a pool.
    policy: HyperdriveBasePolicy
        The policy being executed.
    preview_before_trade: bool
        Whether or not to preview the trade before it is executed.
    liquidate: bool
        If set, will ignore all policy settings and liquidate all open positions.
    randomize_liquidation: bool, optional
        If set, will randomize the order of liquidation trades.
        Defaults to False.
    rng: Generator, optional
        The RNG used to randomize liquidation trades.
        Defaults to None.

    Returns
    -------
    list[TradeResult]
        Returns a list of TradeResult objects, one for each trade made by the agent.
        TradeResult handles any information about the trade, as well as any trade errors.
    """

    if liquidate:
        if rng is None:
            raise ValueError("RNG cannot be None when liquidating.")
        trades: list[Trade[HyperdriveMarketAction]] = _get_liquidation_trades(
            interface, wallet, randomize_liquidation, rng
        )
    else:
        if policy is None:
            raise ValueError("Policy cannot be None when executing agent trades.")
        trades: list[Trade[HyperdriveMarketAction]] = _get_trades(
            interface=interface.get_read_interface(), policy=policy, wallet=wallet
        )

    # Make trades async for this agent. This way, an agent can submit multiple trades for a single block
    # To do this, we need to manually set the nonce, so we get the base transaction count here
    # and pass in an incrementing nonce per call
    # TODO figure out which exception here to retry on
    base_nonce = retry_call(
        DEFAULT_READ_RETRY_COUNT, None, interface.web3.eth.get_transaction_count, account.address, "pending"
    )

    # Here, gather returns results based on original order of trades due to nonce getting explicitly set based
    # on iterating through the list

    # We expect the type here to be BaseException (due to the return type of asyncio.gather),
    # but the underlying exception should be subclassed from Exception.

    # TODO preliminary search shows async tasks has very low overhead:
    # https://stackoverflow.com/questions/55761652/what-is-the-overhead-of-an-asyncio-task
    # However, should probably test the limit number of trades an agent can make in one block
    receipt_or_exception: list[ReceiptBreakdown | BaseException] = await asyncio.gather(
        *[
            _async_match_contract_call_to_trade(
                account,
                interface,
                trade_object,
                nonce=Nonce(base_nonce + i),
                preview_before_trade=preview_before_trade,
            )
            for i, trade_object in enumerate(trades)
        ],
        # Instead of throwing exception, return the exception to the caller here
        return_exceptions=True,
    )

    trade_results = _handle_contract_call_to_trade(receipt_or_exception, trades, interface, account, wallet, policy)

    # TODO to avoid adding a post action in base policy, we only call post action
    # if the policy is a hyperdrive policy. Ideally, we'd allow base classes all the
    # way down
    if isinstance(policy, HyperdriveBasePolicy):
        # Calls the agent with the trade results in case the policy needs to do bookkeeping.
        # We copy a trade results to avoid changing the original trade result for crash reporting.

        # TODO deepcopy may be inefficient here when copying, e.g., trade_result.agent.
        # If this is the case, we can selectively create a new TradeResult object with a subset of data.
        #
        # TODO can't put post_action in agent due to circular import, so we call the policy post_action here
        policy.post_action(interface, deepcopy(trade_results))

    return trade_results


async def async_execute_single_trade(
    interface: HyperdriveReadWriteInterface,
    account: LocalAccount,
    account_wallet: HyperdriveWallet,
    trade_object: Trade[HyperdriveMarketAction],
    execute_policy_post_action: bool,
    preview_before_trade: bool,
    policy: HyperdriveBasePolicy | None = None,
) -> TradeResult:
    """Executes a single trade made by the agent.

    .. note :: This function is not thread safe, as
    (1) the agent's wallet update is not thread safe
    (2) acquiring the nonce for this trade is not thread safe

    Arguments
    ---------
    interface: HyperdriveReadWriteInterface
        The Hyperdrive API interface object.
    account: LocalAccount
        The LocalAccount that is conducting the trade.
    account_wallet: HyperdriveWallet
        The wallet of the account.
    trade_object: Trade[HyperdriveMarketAction]
        The trade to execute.
    execute_policy_post_action: bool
        Whether or not to execute the post_action of the policy after the trade.
    preview_before_trade: bool
        Whether or not to preview the trade before it is executed.
    policy: HyperdriveBasePolicy | None, optional
        The policy attached to the agent. This is only used to potentially call `post_action`
        of the policy.

    Returns
    -------
    TradeResult
        The result of the trade.
    """

    # TODO we likely need to bookkeep nonces here to avoid a race condition when this function
    # is being called asynchronously
    nonce = retry_call(
        DEFAULT_READ_RETRY_COUNT, None, interface.web3.eth.get_transaction_count, account.address, "pending"
    )

    try:
        receipt_or_exception = await _async_match_contract_call_to_trade(
            account,
            interface,
            trade_object,
            nonce,
            preview_before_trade,
        )
    except Exception as e:  # pylint: disable=broad-except
        receipt_or_exception = e

    trade_results = _handle_contract_call_to_trade(
        [receipt_or_exception], [trade_object], interface, account, account_wallet, policy=None
    )

    assert len(trade_results) == 1

    # Some policies still need to bookkeep if single trades are being made. We call that here.
    # TODO to avoid adding a post action in base policy, we only call post action
    # if the policy is a hyperdrive policy. Ideally, we'd allow base classes all the
    # way down
    if execute_policy_post_action and policy is not None:
        # Calls the agent with the trade results in case the policy needs to do bookkeeping.
        # We copy a trade results to avoid changing the original trade result for crash reporting.

        # TODO deepcopy may be inefficient here when copying, e.g., trade_result.agent.
        # If this is the case, we can selectively create a new TradeResult object with a subset of data.
        #
        # TODO can't put post_action in agent due to circular import, so we call the policy post_action here
        policy.post_action(interface, deepcopy(trade_results))

    return trade_results[0]


def _handle_contract_call_to_trade(
    receipt_or_exception: list[ReceiptBreakdown | BaseException],
    trades: list[Trade[HyperdriveMarketAction]],
    interface: HyperdriveReadInterface,
    account: LocalAccount,
    wallet: HyperdriveWallet,
    policy: HyperdriveBasePolicy | None,
) -> list[TradeResult]:
    """Handle the results of executing trades. This function also updates the underlying agent's wallet.

    Arguments
    ---------
    wallet_deltas_or_exception: list[tuple[HyperdriveWalletDeltas, ReceiptBreakdown] | BaseException]
        The results of executing trades. This argument is either the output of
        _async_match_contract_call_to_trade or an exception to crash report.
    trades: list[HyperdriveMarketAction]
        The list of trades that were executed.
    interface: HyperdriveReadInterface
        The read interface for the market.
    account: LocalAccount
        The account that executed the trades.
    wallet: HyperdriveWallet
        The wallet of the account.
    policy: HyperdriveBasePolicy | None
        The policy attached to the agent.

    Returns
    -------
    list[TradeResult]
        Returns the list of trade results.
    """

    # Sanity check
    if len(receipt_or_exception) != len(trades):
        raise AssertionError(
            "The number of wallet deltas should match the number of trades, but does not."
            f"\n{receipt_or_exception=}\n{trades=}"
        )

    trade_results: list[TradeResult] = []
    # Since the list of wallet deltas or exceptions is guaranteed to be in the order
    # of execution, we incrementally update the wallet. Updating the wallet
    # while iterating will ensure the invalid balance check has the most
    # up to date wallet for checking balances.
    for result, trade_object in zip(receipt_or_exception, trades):
        if isinstance(result, Exception):
            trade_result = build_crash_trade_result(result, interface, account, wallet, policy, trade_object)
            # We check for common errors and allow for custom handling of various errors.
            # These functions adjust the trade_result.exception object to add
            # additional arguments describing these detected errors for crash reporting.
            trade_result = check_for_invalid_balance(trade_result, interface)
            trade_result = check_for_insufficient_allowance(trade_result, interface)
            trade_result = check_for_slippage(trade_result)
            trade_result = check_for_min_txn_amount(trade_result)
        else:
            if not isinstance(result, ReceiptBreakdown):
                raise TypeError("The trade result is not the correct type.")
            tx_receipt = result
            trade_result = TradeResult(
                trade_successful=True, account=account, trade_object=trade_object, tx_receipt=tx_receipt
            )
        trade_results.append(trade_result)

    return trade_results


async def _async_match_contract_call_to_trade(
    account: LocalAccount,
    interface: HyperdriveReadWriteInterface,
    trade_envelope: Trade[HyperdriveMarketAction],
    nonce: Nonce,
    preview_before_trade: bool,
) -> ReceiptBreakdown:
    """Match statement that executes the smart contract trade based on the provided type.

    Arguments
    ---------
    account: LocalAccount
        Object containing the wallet address.
    interface: HyperdriveReadWriteInterface
        The Hyperdrive API interface object.
    trade_envelope: Trade[HyperdriveMarketAction]
        A specific Hyperdrive trade requested by the given agent.
    nonce: Nonce, optional
        Override the transaction number assigned to the transaction call from the agent wallet.
    preview_before_trade: bool
        Whether or not to preview the trade before it is executed.

    Returns
    -------
    ReceiptBreakdown
        The result of executing the trade.
    """
    trade = trade_envelope.market_action
    match trade.action_type:
        case HyperdriveActionType.INITIALIZE_MARKET:
            raise ValueError(f"{trade.action_type} not supported!")

        case HyperdriveActionType.OPEN_LONG:
            trade_result = await interface.async_open_long(
                account,
                trade.trade_amount,
                slippage_tolerance=trade.slippage_tolerance,
                gas_limit=trade.gas_limit,
                nonce=nonce,
                preview_before_trade=preview_before_trade,
            )

        case HyperdriveActionType.CLOSE_LONG:
            if not trade.maturity_time:
                raise ValueError("Maturity time was not provided, can't close long position.")
            trade_result = await interface.async_close_long(
                account,
                trade.trade_amount,
                trade.maturity_time,
                slippage_tolerance=trade.slippage_tolerance,
                gas_limit=trade.gas_limit,
                nonce=nonce,
                preview_before_trade=preview_before_trade,
            )

        case HyperdriveActionType.OPEN_SHORT:
            trade_result = await interface.async_open_short(
                account,
                trade.trade_amount,
                slippage_tolerance=trade.slippage_tolerance,
                gas_limit=trade.gas_limit,
                nonce=nonce,
                preview_before_trade=preview_before_trade,
            )

        case HyperdriveActionType.CLOSE_SHORT:
            if not trade.maturity_time:
                raise ValueError("Maturity time was not provided, can't close long position.")
            trade_result = await interface.async_close_short(
                account,
                trade.trade_amount,
                trade.maturity_time,
                slippage_tolerance=trade.slippage_tolerance,
                gas_limit=trade.gas_limit,
                nonce=nonce,
                preview_before_trade=preview_before_trade,
            )

        case HyperdriveActionType.ADD_LIQUIDITY:
            if not trade.min_apr:
                raise AssertionError("min_apr is required for ADD_LIQUIDITY")
            if not trade.max_apr:
                raise AssertionError("max_apr is required for ADD_LIQUIDITY")
            trade_result = await interface.async_add_liquidity(
                account,
                trade.trade_amount,
                trade.min_apr,
                trade.max_apr,
                slippage_tolerance=None,
                gas_limit=trade.gas_limit,
                nonce=nonce,
                preview_before_trade=preview_before_trade,
            )

        case HyperdriveActionType.REMOVE_LIQUIDITY:
            trade_result = await interface.async_remove_liquidity(
                account,
                trade.trade_amount,
                gas_limit=trade.gas_limit,
                nonce=nonce,
                preview_before_trade=preview_before_trade,
            )

        case HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
            trade_result = await interface.async_redeem_withdraw_shares(
                account,
                trade.trade_amount,
                gas_limit=trade.gas_limit,
                nonce=nonce,
                preview_before_trade=preview_before_trade,
            )

        case _:
            # Should never get here
            assert_never(trade.action_type)
    return trade_result
