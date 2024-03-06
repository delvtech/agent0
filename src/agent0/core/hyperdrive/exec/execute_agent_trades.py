"""Main script for running agents on Hyperdrive."""

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
from agent0.ethpy.hyperdrive import HyperdriveReadWriteInterface, ReceiptBreakdown

if TYPE_CHECKING:
    from agent0.core.hyperdrive import HyperdriveAgent


async def async_execute_single_agent_trade(
    agent: HyperdriveAgent,
    interface: HyperdriveReadWriteInterface,
    liquidate: bool,
    randomize_liquidation: bool,
    interactive_mode: bool,
) -> list[TradeResult]:
    """Executes a single agent's trade. This function is async as
    `match_contract_call_to_trade` waits for a transaction receipt.

    Arguments
    ---------
    agent: HyperdriveAgent
        The HyperdriveAgent that is conducting the trade
    interface: HyperdriveReadWriteInterface
        The Hyperdrive API interface object
    liquidate: bool
        If set, will ignore all policy settings and liquidate all open positions
    randomize_liquidation: bool
        If set, will randomize the order of liquidation trades
    interactive_mode: bool
        If set, running in interactive mode

    Returns
    -------
    list[TradeResult]
        Returns a list of TradeResult objects, one for each trade made by the agent
        TradeResult handles any information about the trade, as well as any errors that the trade resulted in
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

    # We expect the type here to be BaseException (due to the return type of asyncio.gather),
    # but the underlying exception should be subclassed from Exception.
    # TODO preliminary search shows async tasks has very low overhead:
    # https://stackoverflow.com/questions/55761652/what-is-the-overhead-of-an-asyncio-task
    # However, should probably test what the limit number of trades an agent can make in one block
    wallet_deltas_or_exception: list[tuple[HyperdriveWalletDeltas, ReceiptBreakdown] | BaseException] = (
        await asyncio.gather(
            *[
                async_match_contract_call_to_trade(agent, interface, trade_object, nonce=Nonce(base_nonce + i))
                for i, trade_object in enumerate(trades)
            ],
            # Instead of throwing exception, return the exception to the caller here
            return_exceptions=True,
        )
    )

    # TODO Here, gather returns results based on original order of trades, but this order isn't guaranteed
    # because of async. Ideally, we should return results based on the order of trades. Can we use nonce here
    # to see order?

    # Sanity check
    if len(wallet_deltas_or_exception) != len(trades):
        raise AssertionError(
            "The number of wallet deltas should match the number of trades, but does not."
            f"\n{wallet_deltas_or_exception=}\n{trades=}"
        )

    # The wallet update after should be fine, since we can see what trades went through
    # and only apply those wallet deltas. Wallet deltas are also invariant to order
    # as long as the transaction went through.
    trade_results = []
    for result, trade_object in zip(wallet_deltas_or_exception, trades):
        if isinstance(result, Exception):
            trade_result = build_crash_trade_result(result, interface, agent, trade_object)
        else:
            assert isinstance(result, tuple)
            assert len(result) == 2
            wallet_delta, tx_receipt = result
            assert isinstance(wallet_delta, HyperdriveWalletDeltas)
            assert isinstance(tx_receipt, ReceiptBreakdown)
            agent.wallet.update(wallet_delta)
            trade_result = TradeResult(
                status=TradeStatus.SUCCESS, agent=agent, trade_object=trade_object, tx_receipt=tx_receipt
            )
        trade_results.append(trade_result)

    # TODO to avoid adding a post action in base policy, we only call post action
    # if the policy is a hyperdrive policy. Ideally, we'd allow base classes all the
    # way down
    if isinstance(agent.policy, HyperdriveBasePolicy):
        # Calls the agent with the trade results in case the policy needs to do bookkeeping
        # We copy a subset of fields from the trade results to avoid changing the original
        # trade result for crash reporting
        # TODO deepcopy may be inefficient here when copying, e.g., trade_result.agent
        # If this is the case, we can selectively create a new TradeResult object with a subset
        # of data
        trade_result_copy = deepcopy(trade_results)
        # TODO can't put post_action in agent due to circular import, so we call the policy post_action here
        agent.policy.post_action(interface, trade_result_copy)

    return trade_results


async def async_execute_agent_trades(
    interface: HyperdriveReadWriteInterface,
    agents: list[HyperdriveAgent],
    liquidate: bool,
    randomize_liquidation: bool = False,
    interactive_mode: bool = False,
) -> list[TradeResult]:
    """Hyperdrive forever into the sunset.

    Arguments
    ---------
    interface: HyperdriveReadWriteInterface
        The Hyperdrive API interface object
    agents: list[HyperdriveAgent]
        A list of HyperdriveAgent that are conducting the trades
    liquidate: bool
        If set, will ignore all policy settings and liquidate all open positions
    randomize_liquidation: bool
        If set, will randomize the order of liquidation trades
    interactive_mode: bool
        Defines if this function is being called in interactive mode

    Returns
    -------
    list[TradeResult]
        Returns a list of TradeResult objects, one for each trade made by the agent
        TradeResult handles any information about the trade, as well as any errors that the trade resulted in
    """
    # Make calls per agent to execute_single_agent_trade
    # Await all trades to finish before continuing
    gathered_trade_results: list[list[TradeResult]] = await asyncio.gather(
        *[
            async_execute_single_agent_trade(agent, interface, liquidate, randomize_liquidation, interactive_mode)
            for agent in agents
            if not agent.done_trading
        ]
    )
    # Flatten list of lists, since agent information is already in TradeResult
    trade_results = [item for sublist in gathered_trade_results for item in sublist]

    # Iterate through trade results, checking for known errors
    out_trade_results = []
    for trade_result in trade_results:
        if trade_result.status == TradeStatus.FAIL:
            # Here, we check for common errors and allow for custom handling of various errors

            # These functions adjust the trade_result.exception object to add
            # additional arguments describing these detected errors for crash reporting
            trade_result = check_for_invalid_balance(trade_result)
            trade_result = check_for_slippage(trade_result)
            trade_result = check_for_min_txn_amount(trade_result)
        out_trade_results.append(trade_result)
    return out_trade_results


async def async_match_contract_call_to_trade(
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
    nonce: Nonce
        Override the transaction number assigned to the transaction call from the agent wallet.

    Returns
    -------
    HyperdriveWalletDeltas
        Deltas to be applied to the agent's wallet.
    """
    # TODO: figure out fees paid
    trade = trade_envelope.market_action
    match trade.action_type:
        case HyperdriveActionType.INITIALIZE_MARKET:
            raise ValueError(f"{trade.action_type} not supported!")

        case HyperdriveActionType.OPEN_LONG:
            trade_result = await interface.async_open_long(
                agent, trade.trade_amount, trade.slippage_tolerance, nonce=nonce
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
                agent, trade.trade_amount, trade.maturity_time, trade.slippage_tolerance, nonce=nonce
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
                agent, trade.trade_amount, trade.slippage_tolerance, nonce=nonce
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
                agent, trade.trade_amount, trade.maturity_time, trade.slippage_tolerance, nonce=nonce
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
            min_apr = trade.min_apr
            assert min_apr, "min_apr is required for ADD_LIQUIDITY"
            max_apr = trade.max_apr
            assert max_apr, "max_apr is required for ADD_LIQUIDITY"
            # TODO implement slippage tolerance for add liquidity
            trade_result = await interface.async_add_liquidity(
                agent, trade.trade_amount, min_apr, max_apr, slippage_tolerance=None, nonce=nonce
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=-trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                lp_tokens=trade_result.lp_amount,
            )

        case HyperdriveActionType.REMOVE_LIQUIDITY:
            trade_result = await interface.async_remove_liquidity(agent, trade.trade_amount, nonce=nonce)
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                lp_tokens=-trade_result.lp_amount,
                withdraw_shares=trade_result.withdrawal_share_amount,
            )

        case HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
            trade_result = await interface.async_redeem_withdraw_shares(agent, trade.trade_amount, nonce=nonce)
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
