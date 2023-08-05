"""Hyperdrive AMM action specification."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

import elfpy.types as types
from elfpy.markets.base import BaseMarketAction
from fixedpointmath import FixedPoint

if TYPE_CHECKING:
    from elfpy.wallet.wallet import Wallet


class HyperdriveActionType(Enum):
    r"""The descriptor of an action in a market"""
    INITIALIZE_MARKET = "initialize_market"

    ADD_LIQUIDITY = "add_liquidity"
    REMOVE_LIQUIDITY = "remove_liquidity"

    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"

    CLOSE_LONG = "close_long"
    CLOSE_SHORT = "close_short"

    REDEEM_WITHDRAW_SHARE = "redeem_withdraw_share"


@types.freezable(frozen=False, no_new_attribs=True)
@dataclass
class HyperdriveMarketAction(BaseMarketAction):
    r"""Market action specification"""
    # these two variables are required to be set by the strategy
    action_type: MarketActionType
    # amount to supply for the action
    trade_amount: FixedPoint  # TODO: should this be a Quantity, not a float? Make sure, then delete fixme
    # the agent's wallet
    wallet: Wallet
    # slippage tolerance percent where 0.01 would be a 1% tolerance
    slippage_tolerance: FixedPoint | None = None
    # mint time is set only for trades that act on existing positions (close long or close short)
    mint_time: FixedPoint | None = None
    # maturity time is set only for trades that act on existing positions (close long or close short)
    maturity_time: FixedPoint | None = None
