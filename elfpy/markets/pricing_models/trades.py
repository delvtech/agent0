"""Trade related classes and functions"""
from dataclasses import dataclass


import elfpy.markets.hyperdrive as hyperdrive
import elfpy.agents.agent as agent
import elfpy.types as types


@types.freezable(frozen=True, no_new_attribs=True)
@dataclass
class TradeBreakdown:
    r"""A granular breakdown of a trade.

    This includes information relating to fees and slippage.
    """

    without_fee_or_slippage: float
    with_fee: float
    without_fee: float
    fee: float


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
    market_result: hyperdrive.MarketTradeResult
    breakdown: TradeBreakdown

    def __str__(self):
        output_string = (
            "TradeResult(\n"
            "\tuser_results(\n"
            f"\t\t{self.user_result.d_base=},\n"
            f"\t\t{self.user_result.d_bonds=},\n"
            "\t),\n"
            "\tmarket_result(\n"
            f"\t\t{self.market_result.d_base=},\n"
            f"\t\t{self.market_result.d_bonds=},\n"
            "\t),\n"
            "\tbreakdown(\n"
            f"\t\t{self.breakdown.without_fee_or_slippage=},\n"
            f"\t\t{self.breakdown.with_fee=},\n"
            f"\t\t{self.breakdown.without_fee=},\n"
            f"\t\t{self.breakdown.fee=},\n"
            "\t)\n"
            ")"
        )
        return output_string
