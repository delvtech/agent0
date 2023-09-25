"""Main script for running agents on Hyperdrive."""
from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, NoReturn

from agent0.base import Quantity, TokenType
from agent0.hyperdrive.state import HyperdriveActionType, HyperdriveMarketAction, HyperdriveWalletDeltas, Long, Short
from elfpy import types
from elfpy.markets.hyperdrive import HyperdriveMarket
from ethpy.base import UnknownBlockError
from ethpy.hyperdrive import HyperdriveInterface, get_hyperdrive_market
from fixedpointmath import FixedPoint

if TYPE_CHECKING:
    from agent0.hyperdrive.agents import HyperdriveAgent

# TODO: Fix these up when we refactor this file
# pylint: disable=too-many-locals


def assert_never(arg: NoReturn) -> NoReturn:
    """Helper function for exhaustive matching on ENUMS.

    .. note::
        This ensures that all ENUM values are checked, via an exhaustive match:
        https://github.com/microsoft/pyright/issues/2569
    """
    assert False, f"Unhandled type: {type(arg).__name__}"


async def async_execute_single_agent_trade(
    agent: HyperdriveAgent,
    hyperdrive: HyperdriveInterface,
    hyperdrive_market: HyperdriveMarket,
) -> None:
    """Executes a single agent's trade. This function is async as
    `match_contract_call_to_trade` waits for a transaction receipt.

    Arguments
    ---------
    agent: HyperdriveAgent
        The HyperdriveAgent that is conducting the trade
    hyperdrive : HyperdriveInterface
        The Hyperdrive API interface object
    hyperdrive_market: HyperdriveMarket:
        The hyperdrive market state
    """
    trades: list[types.Trade[HyperdriveMarketAction]] = agent.get_trades(market=hyperdrive_market)
    for trade_object in trades:
        logging.info(
            "AGENT %s to perform %s for %g",
            str(agent.checksum_address),
            trade_object.market_action.action_type,
            float(trade_object.market_action.trade_amount),
        )
        try:
            wallet_deltas = await async_match_contract_call_to_trade(agent, hyperdrive, trade_object)
            agent.wallet.update(wallet_deltas)
        except UnknownBlockError as exc:
            logging.error(exc)


async def async_execute_agent_trades(
    hyperdrive: HyperdriveInterface,
    agents: list[HyperdriveAgent],
) -> None:
    """Hyperdrive forever into the sunset.

    Arguments
    ---------
    hyperdrive : HyperdriveInterface
        The Hyperdrive API interface object
    agents : list[HyperdriveAgent]
        A list of HyperdriveAgent that are conducting the trades
    """
    # NOTE: This might _not_ be the latest market, due to async
    # get latest market
    hyperdrive_market = get_hyperdrive_market(hyperdrive.web3, hyperdrive.hyperdrive_contract)
    # Make calls per agent to execute_single_agent_trade
    # Await all trades to finish before continuing
    await asyncio.gather(*[async_execute_single_agent_trade(agent, hyperdrive, hyperdrive_market) for agent in agents])


async def async_match_contract_call_to_trade(
    agent: HyperdriveAgent,
    hyperdrive: HyperdriveInterface,
    trade_envelope: types.Trade[HyperdriveMarketAction],
) -> HyperdriveWalletDeltas:
    """Match statement that executes the smart contract trade based on the provided type.

    Arguments
    ---------
    agent : HyperdriveAgent
        Object containing a wallet address and Elfpy Agent for determining trades
    hyperdrive : HyperdriveInterface
        The Hyperdrive API interface object
    trade_object : Trade
        A specific trade requested by the given agent

    Returns
    -------
    HyperdriveWalletDeltas
        Deltas to be applied to the agent's wallet

    """
    # TODO: figure out fees paid
    # pylint: disable=too-many-statements
    trade = trade_envelope.market_action
    # TODO: The following variables are hard coded for now, but should be specified in the trade spec
    min_apr = int(1)
    max_apr = FixedPoint(1).scaled_value
    match trade.action_type:
        case HyperdriveActionType.INITIALIZE_MARKET:
            raise ValueError(f"{trade.action_type} not supported!")

        case HyperdriveActionType.OPEN_LONG:
            trade_result = await hyperdrive.async_open_long(agent, trade.trade_amount, trade.slippage_tolerance)
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=-trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                longs={trade_result.maturity_time_seconds: Long(trade_result.bond_amount)},
            )

        case HyperdriveActionType.CLOSE_LONG:
            if not trade.maturity_time:
                raise ValueError("Mint time was not provided, can't close long position.")
            trade_result = await hyperdrive.async_close_long(
                agent, trade.trade_amount, trade.maturity_time, trade.slippage_tolerance
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                longs={trade.maturity_time: Long(-trade_result.bond_amount)},
            )

        case HyperdriveActionType.OPEN_SHORT:
            trade_result = await hyperdrive.async_open_short(agent, trade.trade_amount, trade.slippage_tolerance)
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=-trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                shorts={trade_result.maturity_time_seconds: Short(balance=trade_result.bond_amount)},
            )

        case HyperdriveActionType.CLOSE_SHORT:
            if not trade.maturity_time:
                raise ValueError("Mint time was not provided, can't close long position.")
            trade_result = await hyperdrive.async_close_short(
                agent, trade.trade_amount, trade.maturity_time, trade.slippage_tolerance
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                shorts={trade.maturity_time: Short(balance=-trade_result.bond_amount)},
            )

        case HyperdriveActionType.ADD_LIQUIDITY:
            trade_result = await hyperdrive.async_add_liquidity(
                agent, trade.trade_amount, FixedPoint(min_apr), FixedPoint(max_apr)
            )
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=-trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                lp_tokens=trade_result.lp_amount,
            )

        case HyperdriveActionType.REMOVE_LIQUIDITY:
            trade_result = await hyperdrive.async_remove_liquidity(agent, trade.trade_amount)
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                lp_tokens=-trade_result.lp_amount,
                withdraw_shares=trade_result.withdrawal_share_amount,
            )

        case HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
            trade_result = await hyperdrive.async_redeem_withdraw_shares(agent, trade.trade_amount)
            wallet_deltas = HyperdriveWalletDeltas(
                balance=Quantity(
                    amount=trade_result.base_amount,
                    unit=TokenType.BASE,
                ),
                withdraw_shares=-trade_result.withdrawal_share_amount,
            )

        case _:
            assert_never(trade.action_type)
    return wallet_deltas
