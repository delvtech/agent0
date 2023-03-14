"""Trade related classes and functions"""
from dataclasses import dataclass
from decimal import Decimal

import elfpy.types as types
import elfpy.agents.agent as agent
import elfpy.markets.hyperdrive.hyperdrive_actions as hyperdrive_actions


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class TradeBreakdown:
    r"""A granular breakdown of a trade.

    This includes information relating to fees and slippage.

    Attributes
    ----------
    without_fee_or_slippage: float
        The amount the user pays without fees or slippage. The units
        are always in terms of bonds or base, depending on input.
    with_fee: float
        The fee the user pays. The units are always in terms of bonds or
        base.
    without_fee: float
        The amount the user pays with fees and slippage. The units are
        always in terms of bonds or base.
    fee: float
        The amount the user pays with slippage and no fees. The units are
        always in terms of bonds or base.
    """

    without_fee_or_slippage: Decimal
    with_fee: Decimal
    without_fee: Decimal
    fee: Decimal


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class TradeResult:
    r"""The result of performing a trade.

    This includes granular information about the trade details,
    including the amount of fees collected and the total delta.
    Additionally, breakdowns for the updates that should be applied
    to the user and the market are computed.
    """

    user_result: agent.AgentTradeResult
    market_result: hyperdrive_actions.MarketActionResult
    breakdown: TradeBreakdown
