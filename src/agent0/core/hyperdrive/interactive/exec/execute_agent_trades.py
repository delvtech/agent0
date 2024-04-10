"""Execute trades from agents and manage errors."""

from __future__ import annotations

import asyncio
from copy import deepcopy
from typing import TYPE_CHECKING

from web3.types import Nonce

from agent0.core.base import Quantity, TokenType, Trade
from agent0.core.hyperdrive import (
    HyperdriveActionType,
    HyperdriveMarketAction,
    HyperdriveWalletDeltas,
    Long,
    Short,
    TradeResult,
    TradeStatus,
)
from agent0.core.hyperdrive.crash_report import (
    build_crash_trade_result,
    check_for_invalid_balance,
    check_for_min_txn_amount,
    check_for_slippage,
)
from agent0.core.hyperdrive.policies import HyperdriveBasePolicy
from agent0.core.test_utils import assert_never
from agent0.ethpy.base import retry_call
from agent0.ethpy.base.transactions import DEFAULT_READ_RETRY_COUNT
from agent0.ethpy.hyperdrive import HyperdriveReadInterface, HyperdriveReadWriteInterface, ReceiptBreakdown

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveAgent


async def async_execute_agent_trades(
    interface: HyperdriveReadWriteInterface,
    agent: HyperdriveAgent,
    liquidate: bool,
    randomize_liquidation: bool = False,
    interactive_mode: bool = False,
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
    agent: HyperdriveAgent
        The HyperdriveAgent that is conducting the trade.
    liquidate: bool
        If set, will ignore all policy settings and liquidate all open positions.
    randomize_liquidation: bool, optional
        If set, will randomize the order of liquidation trades.
        Defaults to False.
    interactive_mode: bool, optional
        If set, running in interactive mode.
        Defaults to False.

    Returns
    -------
    list[TradeResult]
        Returns a list of TradeResult objects, one for each trade made by the agent.
        TradeResult handles any information about the trade, as well as any trade errors.
    """

    if liquidate:
        # TODO: test this option
        trades: list[Trade[HyperdriveMarketAction]] = agent.get_liquidation_trades(
            interface, randomize_liquidation, interactive_mode
        )
    else:
        trades: list[Trade[HyperdriveMarketAction]] = agent.get_trades(interface=interface.get_read_interface())

    # Make trades async for this agent. This way, an agent can submit multiple trades for a single block
    # To do this, we need to manually set the nonce, so we get the base transaction count here
    # and pass in an incrementing nonce per call
    # TODO figure out which exception here to retry on
    base_nonce = retry_call(
        DEFAULT_READ_RETRY_COUNT, None, interface.web3.eth.get_transaction_count, agent.checksum_address
    )

    # Here, gather returns results based on original order of trades due to nonce getting explicitly set based
    # on iterating through the list

    # We expect the type here to be BaseException (due to the return type of asyncio.gather),
    # but the underlying exception should be subclassed from Exception.

    # TODO preliminary search shows async tasks has very low overhead:
    # https://stackoverflow.com/questions/55761652/what-is-the-overhead-of-an-asyncio-task
    # However, should probably test the limit number of trades an agent can make in one block
    wallet_deltas_or_exception: list[tuple[HyperdriveWalletDeltas, ReceiptBreakdown] | BaseException] = (
        await asyncio.gather(
            *[
                _async_match_contract_call_to_trade(agent, interface, trade_object, nonce=Nonce(base_nonce + i))
                for i, trade_object in enumerate(trades)
            ],
            # Instead of throwing exception, return the exception to the caller here
            return_exceptions=True,
        )
    )

    trade_results, wallet_updates = _handle_contract_call_to_trade(wallet_deltas_or_exception, trades, interface, agent)

    # The wallet update after should be fine, since we can see what trades went through
    # and only apply those wallet deltas. Wallet deltas are also invariant to order
    # as long as the transaction went through.
    for wallet_delta in wallet_updates:
        agent.wallet.update(wallet_delta)

    # TODO to avoid adding a post action in base policy, we only call post action
    # if the policy is a hyperdrive policy. Ideally, we'd allow base classes all the
    # way down
    if isinstance(agent.policy, HyperdriveBasePolicy):
        # Calls the agent with the trade results in case the policy needs to do bookkeeping.
        # We copy a trade results to avoid changing the original trade result for crash reporting.

        # TODO deepcopy may be inefficient here when copying, e.g., trade_result.agent.
        # If this is the case, we can selectively create a new TradeResult object with a subset of data.
        #
        # TODO can't put post_action in agent due to circular import, so we call the policy post_action here
        agent.policy.post_action(interface, deepcopy(trade_results))

    return trade_results


async def async_execute_single_trade(
    interface: HyperdriveReadWriteInterface,
    agent: HyperdriveAgent,
    trade_object: Trade[HyperdriveMarketAction],
    execute_policy_post_action: bool,
) -> TradeResult:
    """Executes a single trade made by the agent.

    .. note :: This function is not thread safe, as
    (1) the agent's wallet update is not thread safe
    (2) acquiring the nonce for this trade is not thread safe

    Arguments
    ---------
    interface: HyperdriveReadWriteInterface
        The Hyperdrive API interface object.
    agent: HyperdriveAgent
        The HyperdriveAgent that is conducting the trade.
    trade_object: Trade[HyperdriveMarketAction]
        The trade to execute.
    execute_policy_post_action: bool
        Whether or not to execute the post_action of the policy after the trade.

    Returns
    -------
    TradeResult
        The result of the trade.
    """

    # TODO we likely need to bookkeep nonces here to avoid a race condition when this function
    # is being called asynchronously
    nonce = retry_call(DEFAULT_READ_RETRY_COUNT, None, interface.web3.eth.get_transaction_count, agent.checksum_address)

    try:
        wallet_delta_or_exception = await _async_match_contract_call_to_trade(agent, interface, trade_object, nonce)
    except Exception as e:  # pylint: disable=broad-except
        wallet_delta_or_exception = e

    trade_results, wallet_updates = _handle_contract_call_to_trade(
        [wallet_delta_or_exception], [trade_object], interface, agent
    )

    assert len(trade_results) == 1
    # Wallet updates will be 0 if the trade failed
    assert len(wallet_updates) <= 1

    for wallet_delta in wallet_updates:
        agent.wallet.update(wallet_delta)

    # Some policies still need to bookkeep if single trades are being made. We call that here.
    # TODO to avoid adding a post action in base policy, we only call post action
    # if the policy is a hyperdrive policy. Ideally, we'd allow base classes all the
    # way down
    if execute_policy_post_action and isinstance(agent.policy, HyperdriveBasePolicy):
        # Calls the agent with the trade results in case the policy needs to do bookkeeping.
        # We copy a trade results to avoid changing the original trade result for crash reporting.

        # TODO deepcopy may be inefficient here when copying, e.g., trade_result.agent.
        # If this is the case, we can selectively create a new TradeResult object with a subset of data.
        #
        # TODO can't put post_action in agent due to circular import, so we call the policy post_action here
        agent.policy.post_action(interface, deepcopy(trade_results))

    return trade_results[0]


def _handle_contract_call_to_trade(
    wallet_deltas_or_exception: list[tuple[HyperdriveWalletDeltas, ReceiptBreakdown] | BaseException],
    trades: list[Trade[HyperdriveMarketAction]],
    interface: HyperdriveReadInterface,
    agent: HyperdriveAgent,
):
    """Handle the results of executing trades.

    Arguments
    ---------
    wallet_deltas_or_exception: list[tuple[HyperdriveWalletDeltas, ReceiptBreakdown] | BaseException]
        The results of executing trades. This argument is either the output of
        _async_match_contract_call_to_trade or an exception to crash report.
    trades: list[HyperdriveMarketAction]
        The list of trades that were executed.
    interface: HyperdriveReadInterface
        The read interface for the market.
    agent: HyperdriveAgent
        The agent that executed the trades.

    Returns
    -------
    Tuple[list[TradeResult], list[HyperdriveWalletDeltas]]
        Returns the list of trade results, as well as any wallet deltas that need to be
        applied to the agent.
    """

    # Sanity check
    if len(wallet_deltas_or_exception) != len(trades):
        raise AssertionError(
            "The number of wallet deltas should match the number of trades, but does not."
            f"\n{wallet_deltas_or_exception=}\n{trades=}"
        )

    trade_results: list[TradeResult] = []
    wallet_deltas: list[HyperdriveWalletDeltas] = []
    for result, trade_object in zip(wallet_deltas_or_exception, trades):
        if isinstance(result, Exception):
            trade_result = build_crash_trade_result(result, interface, agent, trade_object)
            # We check for common errors and allow for custom handling of various errors.
            # These functions adjust the trade_result.exception object to add
            # additional arguments describing these detected errors for crash reporting.
            trade_result = check_for_invalid_balance(trade_result)
            trade_result = check_for_slippage(trade_result)
            trade_result = check_for_min_txn_amount(trade_result)
        else:
            if not isinstance(result, tuple):
                raise TypeError("The trade result is not the correct type.")
            if not len(result) == 2:
                raise AssertionError("The trade result is improperly formatted.")
            wallet_delta, tx_receipt = result
            if not isinstance(wallet_delta, HyperdriveWalletDeltas) or not isinstance(tx_receipt, ReceiptBreakdown):
                raise TypeError("The wallet deltas or the transaction receipt is not the correct type.")
            wallet_deltas.append(wallet_delta)
            trade_result = TradeResult(
                status=TradeStatus.SUCCESS, agent=agent, trade_object=trade_object, tx_receipt=tx_receipt
            )
        trade_results.append(trade_result)

    return trade_results, wallet_deltas


async def _async_match_contract_call_to_trade(
    agent: HyperdriveAgent,
    interface: HyperdriveReadWriteInterface,
    trade_envelope: Trade[HyperdriveMarketAction],
    nonce: Nonce,
) -> tuple[HyperdriveWalletDeltas, ReceiptBreakdown]:
    """Match statement that executes the smart contract trade based on the provided type.

    Arguments
    ---------
    agent: HyperdriveAgent
        Object containing a wallet address and Agent for determining trades.
    interface: HyperdriveReadWriteInterface
        The Hyperdrive API interface object.
    trade_envelope: Trade[HyperdriveMarketAction]
        A specific Hyperdrive trade requested by the given agent.
    nonce: Nonce, optional
        Override the transaction number assigned to the transaction call from the agent wallet.

    Returns
    -------
    HyperdriveWalletDeltas
        Deltas to be applied to the agent's wallet.
    """
    trade = trade_envelope.market_action
    match trade.action_type:
        case HyperdriveActionType.INITIALIZE_MARKET:
            raise ValueError(f"{trade.action_type} not supported!")

        case HyperdriveActionType.OPEN_LONG:
            trade_result = await interface.async_open_long(
                agent,
                trade.trade_amount,
                slippage_tolerance=trade.slippage_tolerance,
                gas_limit=trade.gas_limit,
                nonce=nonce,
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=-trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                longs={
                    trade_result.maturity_time_seconds: Long(
                        balance=trade_result.bond_amount, maturity_time=trade_result.maturity_time_seconds
                    )
                },
            )

        case HyperdriveActionType.CLOSE_LONG:
            if not trade.maturity_time:
                raise ValueError("Maturity time was not provided, can't close long position.")
            trade_result = await interface.async_close_long(
                agent,
                trade.trade_amount,
                trade.maturity_time,
                slippage_tolerance=trade.slippage_tolerance,
                gas_limit=trade.gas_limit,
                nonce=nonce,
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                longs={
                    trade.maturity_time: Long(
                        balance=-trade_result.bond_amount, maturity_time=trade_result.maturity_time_seconds
                    )
                },
            )

        case HyperdriveActionType.OPEN_SHORT:
            trade_result = await interface.async_open_short(
                agent,
                trade.trade_amount,
                slippage_tolerance=trade.slippage_tolerance,
                gas_limit=trade.gas_limit,
                nonce=nonce,
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=-trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                shorts={
                    trade_result.maturity_time_seconds: Short(
                        balance=trade_result.bond_amount, maturity_time=trade_result.maturity_time_seconds
                    )
                },
            )

        case HyperdriveActionType.CLOSE_SHORT:
            if not trade.maturity_time:
                raise ValueError("Maturity time was not provided, can't close long position.")
            trade_result = await interface.async_close_short(
                agent,
                trade.trade_amount,
                trade.maturity_time,
                slippage_tolerance=trade.slippage_tolerance,
                gas_limit=trade.gas_limit,
                nonce=nonce,
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                shorts={
                    trade.maturity_time: Short(
                        balance=-trade_result.bond_amount, maturity_time=trade_result.maturity_time_seconds
                    )
                },
            )

        case HyperdriveActionType.ADD_LIQUIDITY:
            if not trade.min_apr:
                raise AssertionError("min_apr is required for ADD_LIQUIDITY")
            if not trade.max_apr:
                raise AssertionError("max_apr is required for ADD_LIQUIDITY")
            trade_result = await interface.async_add_liquidity(
                agent,
                trade.trade_amount,
                trade.min_apr,
                trade.max_apr,
                slippage_tolerance=None,
                gas_limit=trade.gas_limit,
                nonce=nonce,
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=-trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                lp_tokens=trade_result.lp_amount,
            )

        case HyperdriveActionType.REMOVE_LIQUIDITY:
            trade_result = await interface.async_remove_liquidity(
                agent, trade.trade_amount, gas_limit=trade.gas_limit, nonce=nonce
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                lp_tokens=-trade_result.lp_amount,
                withdraw_shares=trade_result.withdrawal_share_amount,
            )

        case HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
            trade_result = await interface.async_redeem_withdraw_shares(
                agent, trade.trade_amount, gas_limit=trade.gas_limit, nonce=nonce
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                withdraw_shares=-trade_result.withdrawal_share_amount,
            )

        case _:
            # Should never get here
            assert_never(trade.action_type)
    return wallet_deltas, trade_result
