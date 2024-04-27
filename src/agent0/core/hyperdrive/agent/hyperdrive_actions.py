"""Hyperdrive AMM action specification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fixedpointmath import FixedPoint

from agent0.core.base import BaseMarketAction, MarketType, Trade


class HyperdriveActionType(Enum):
    r"""The descriptor of an action in a market."""

    INITIALIZE_MARKET = "initialize_market"

    OPEN_LONG = "open_long"
    CLOSE_LONG = "close_long"

    OPEN_SHORT = "open_short"
    CLOSE_SHORT = "close_short"

    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"
    REDEEM_WITHDRAW_SHARE = "redeem_withdraw_share"


# TODO: consolidate these arguments (pass in just the config?)
# these functions have lots of arguments
# pylint: disable=too-many-arguments
# ruff: noqa: PLR0913


# pylint: disable=too-many-instance-attributes
@dataclass
class HyperdriveMarketAction(BaseMarketAction[HyperdriveActionType]):
    r"""Market action specification."""

    # these two variables are required to be set by the strategy
    action_type: HyperdriveActionType
    # amount to supply for the action
    trade_amount: FixedPoint  # TODO: should this be a Quantity, not a float? Make sure, then delete fixme
    # maturity time is set only for trades that act on existing positions (close long or close short)
    maturity_time: int | None = None
    # slippage tolerance percent where 0.01 would be a 1% tolerance
    slippage_tolerance: FixedPoint | None = None
    # maximum amount of gas to be used for the transaction
    gas_limit: int | None = None
    # gas price base multiple
    base_fee_multiple: float | None = None
    # gas price priority multipe
    priority_fee_multiple: float | None = None
    # min_apr and max_apr used only for add_liquidity trades to control slippage
    min_apr: FixedPoint = FixedPoint(scaled_value=1)
    max_apr: FixedPoint = FixedPoint(scaled_value=2**256 - 1)


def open_long_trade(
    trade_amount: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    base_fee_multiple: float | None = None,
    priority_fee_multiple: float | None = None,
    gas_limit: int | None = None,
) -> Trade[HyperdriveMarketAction]:
    """Return a trade object for opening a long.

    Arguments
    ---------
    trade_amount: FixedPoint
        The amount of base you wish to use to open a long.
    slippage_tolerance: FixedPoint, optional
        Amount of slippage allowed from the trade.
        If given, then the trade will not execute unless the slippage is below this value.
        If not given, then execute the trade regardless of the slippage.
    base_fee_multiple: float | None, optional
        The base fee multiple for the transaction.
    priority_fee_multiple: float | None, optional
        The priority fee multiple for the transaction.
    gas_limit: int | None, optional
        The maximum amount of gas used by the transaction.
        Defaults to `eth_estimateGas` RPC output.

    Returns
    -------
    Trade[HyperdriveMarketAction]
        The trade object for opening a long in a Hyperdrive pool.
    """
    return Trade(
        market_type=MarketType.HYPERDRIVE,
        market_action=HyperdriveMarketAction(
            action_type=HyperdriveActionType.OPEN_LONG,
            trade_amount=trade_amount,
            slippage_tolerance=slippage_tolerance,
            base_fee_multiple=base_fee_multiple,
            priority_fee_multiple=priority_fee_multiple,
            gas_limit=gas_limit,
        ),
    )


def close_long_trade(
    trade_amount: FixedPoint,
    maturity_time: int,
    slippage_tolerance: FixedPoint | None = None,
    base_fee_multiple: float | None = None,
    priority_fee_multiple: float | None = None,
    gas_limit: int | None = None,
) -> Trade[HyperdriveMarketAction]:
    """Return a trade object for closing a long.

    Arguments
    ---------
    trade_amount: FixedPoint
        The amount of bonds you wish to close.
    maturity_time: int
        The token maturity time in seconds.
    slippage_tolerance: FixedPoint, optional
        Amount of slippage allowed from the trade.
        If given, then the trade will not execute unless the slippage is below this value.
        If not given, then execute the trade regardless of the slippage.
    base_fee_multiple: float | None, optional
        The base fee multiple for the transaction.
    priority_fee_multiple: float | None, optional
        The priority fee multiple for the transaction.
    gas_limit: int | None, optional
        The maximum amount of gas used by the transaction.
        Defaults to `eth_estimateGas` RPC output.

    Returns
    -------
    Trade[HyperdriveMarketAction]
        The trade object for closing a long in a Hyperdrive pool.
    """
    return Trade(
        market_type=MarketType.HYPERDRIVE,
        market_action=HyperdriveMarketAction(
            action_type=HyperdriveActionType.CLOSE_LONG,
            trade_amount=trade_amount,
            maturity_time=maturity_time,
            slippage_tolerance=slippage_tolerance,
            base_fee_multiple=base_fee_multiple,
            priority_fee_multiple=priority_fee_multiple,
            gas_limit=gas_limit,
        ),
    )


def open_short_trade(
    trade_amount: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    base_fee_multiple: float | None = None,
    priority_fee_multiple: float | None = None,
    gas_limit: int | None = None,
) -> Trade[HyperdriveMarketAction]:
    """Return a trade object for opening a short.

    Arguments
    ---------
    trade_amount: FixedPoint
        The amount of bonds you wish to short.
    slippage_tolerance: FixedPoint, optional
        Amount of slippage allowed from the trade.
        If given, then the trade will not execute unless the slippage is below this value.
        If not given, then execute the trade regardless of the slippage.
    base_fee_multiple: float | None, optional
        The base fee multiple for the transaction.
    priority_fee_multiple: float | None, optional
        The priority fee multiple for the transaction.
    gas_limit: int | None, optional
        The maximum amount of gas used by the transaction.
        Defaults to `eth_estimateGas` RPC output.

    Returns
    -------
    Trade[HyperdriveMarketAction]
        The trade object for opening a short in a Hyperdrive pool.
    """
    return Trade(
        market_type=MarketType.HYPERDRIVE,
        market_action=HyperdriveMarketAction(
            action_type=HyperdriveActionType.OPEN_SHORT,
            trade_amount=trade_amount,
            slippage_tolerance=slippage_tolerance,
            base_fee_multiple=base_fee_multiple,
            priority_fee_multiple=priority_fee_multiple,
            gas_limit=gas_limit,
        ),
    )


def close_short_trade(
    trade_amount: FixedPoint,
    maturity_time: int,
    slippage_tolerance: FixedPoint | None = None,
    base_fee_multiple: float | None = None,
    priority_fee_multiple: float | None = None,
    gas_limit: int | None = None,
) -> Trade[HyperdriveMarketAction]:
    """Return a trade object for closing a short.

    Arguments
    ---------
    trade_amount: FixedPoint
        The amount of bonds you wish to close.
    maturity_time: int
        The token maturity time in seconds.
    slippage_tolerance: FixedPoint, optional
        Amount of slippage allowed from the trade.
        If given, then the trade will not execute unless the slippage is below this value.
        If not given, then execute the trade regardless of the slippage.
    base_fee_multiple: float | None, optional
        The base fee multiple for the transaction.
    priority_fee_multiple: float | None, optional
        The priority fee multiple for the transaction.
    gas_limit: int | None, optional
        The maximum amount of gas used by the transaction.
        Defaults to `eth_estimateGas` RPC output.

    Returns
    -------
    Trade[HyperdriveMarketAction]
        The trade object for closing a short in a Hyperdrive pool.
    """
    return Trade(
        market_type=MarketType.HYPERDRIVE,
        market_action=HyperdriveMarketAction(
            action_type=HyperdriveActionType.CLOSE_SHORT,
            trade_amount=trade_amount,
            maturity_time=maturity_time,
            slippage_tolerance=slippage_tolerance,
            base_fee_multiple=base_fee_multiple,
            priority_fee_multiple=priority_fee_multiple,
            gas_limit=gas_limit,
        ),
    )


def add_liquidity_trade(
    trade_amount: FixedPoint,
    base_fee_multiple: float | None = None,
    priority_fee_multiple: float | None = None,
    gas_limit: int | None = None,
    min_apr: FixedPoint | None = None,
    max_apr: FixedPoint | None = None,
) -> Trade[HyperdriveMarketAction]:
    """Return a trade object for adding liquidity.

    Arguments
    ---------
    trade_amount: FixedPoint
        The amount of liquidity you wish to add to the pool.
    base_fee_multiple: float | None, optional
        The base fee multiple for the transaction.
    priority_fee_multiple: float | None, optional
        The priority fee multiple for the transaction.
    gas_limit: int | None, optional
        The maximum amount of gas used by the transaction.
        Defaults to `eth_estimateGas` RPC output.
    min_apr: FixedPoint, optional
        Minimum allowable APR after liquidity is added.
        If this is not met, the trade will not execute.
        Defaults to the minimum solidity FixedPoint (1e-18)
    max_apr: FixedPoint, optional
        Maximum allowable APR after liquidity is added.
        If this is not met, the trade will not execute.
        Defaults to the maximum solidity FixedPoint (2**256-1)

    Returns
    -------
    Trade[HyperdriveMarketAction]
        The trade object for adding liquidity to a Hyperdrive pool.
    """
    if min_apr is None:
        min_apr = FixedPoint(scaled_value=1)
    if max_apr is None:
        max_apr = FixedPoint(scaled_value=2**256 - 1)

    return Trade(
        market_type=MarketType.HYPERDRIVE,
        market_action=HyperdriveMarketAction(
            action_type=HyperdriveActionType.ADD_LIQUIDITY,
            trade_amount=trade_amount,
            base_fee_multiple=base_fee_multiple,
            priority_fee_multiple=priority_fee_multiple,
            gas_limit=gas_limit,
            min_apr=min_apr,
            max_apr=max_apr,
        ),
    )


def remove_liquidity_trade(
    trade_amount: FixedPoint,
    slippage_tolerance: FixedPoint | None = None,
    base_fee_multiple: float | None = None,
    priority_fee_multiple: float | None = None,
    gas_limit: int | None = None,
) -> Trade[HyperdriveMarketAction]:
    """Return a trade object for removing liquidity.

    Arguments
    ---------
    trade_amount: FixedPoint
        The amount of liquidity you wish to remove from the pool.
    slippage_tolerance: FixedPoint, optional
        Amount of slippage allowed from the trade.
        If given, then the trade will not execute unless the slippage is below this value.
        If not given, then execute the trade regardless of the slippage.
    base_fee_multiple: float | None, optional
        The base fee multiple for the transaction.
    priority_fee_multiple: float | None, optional
        The priority fee multiple for the transaction.
    gas_limit: int | None, optional
        The maximum amount of gas used by the transaction.
        Defaults to `eth_estimateGas` RPC output.

    Returns
    -------
    Trade[HyperdriveMarketAction]
        The trade object for removing liquidity from a Hyperdrive pool.

    .. warning::
        Slippage tolerance is not implemented for remove liquidity trades, field will be ignored.
    """
    return Trade(
        market_type=MarketType.HYPERDRIVE,
        market_action=HyperdriveMarketAction(
            action_type=HyperdriveActionType.REMOVE_LIQUIDITY,
            trade_amount=trade_amount,
            slippage_tolerance=slippage_tolerance,
            base_fee_multiple=base_fee_multiple,
            priority_fee_multiple=priority_fee_multiple,
            gas_limit=gas_limit,
        ),
    )


def redeem_withdraw_shares_trade(
    trade_amount: FixedPoint,
    base_fee_multiple: float | None = None,
    priority_fee_multiple: float | None = None,
    gas_limit: int | None = None,
) -> Trade[HyperdriveMarketAction]:
    """Return a trade object for redeeming withdraw shares.

    Arguments
    ---------
    trade_amount: FixedPoint
        The amount of withdraw shares you wish to redeem from the pool.
    base_fee_multiple: float | None, optional
        The base fee multiple for the transaction.
    priority_fee_multiple: float | None, optional
        The priority fee multiple for the transaction.
    gas_limit: int | None, optional
        The maximum amount of gas used by the transaction.
        Defaults to `eth_estimateGas` RPC output.

    Returns
    -------
    Trade[HyperdriveMarketAction]
        The trade object for redeeming withdraw shares from a Hyperdrive pool.
    """
    # TODO implement slippage tolerance for withdrawal
    return Trade(
        market_type=MarketType.HYPERDRIVE,
        market_action=HyperdriveMarketAction(
            action_type=HyperdriveActionType.REDEEM_WITHDRAW_SHARE,
            trade_amount=trade_amount,
            base_fee_multiple=base_fee_multiple,
            priority_fee_multiple=priority_fee_multiple,
            gas_limit=gas_limit,
        ),
    )
