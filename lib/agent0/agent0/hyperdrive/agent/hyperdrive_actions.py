"""Hyperdrive AMM action specification."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from fixedpointmath import FixedPoint

from agent0.base import BaseMarketAction


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
    # min_apr and max_apr used only for add_liquidity trades to control slippage
    min_apr: FixedPoint = FixedPoint(scaled_value=1)
    max_apr: FixedPoint = FixedPoint(scaled_value=2**256 - 1)
