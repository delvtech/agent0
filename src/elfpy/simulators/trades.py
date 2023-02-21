from enum import Enum
from dataclasses import dataclass


from elfpy.types import freezable


class TokenType(Enum):
    r"""A type of token"""

    BASE = "base"
    PT = "pt"


@dataclass
class Quantity:
    r"""An amount with a unit"""

    amount: float
    unit: TokenType


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class TradeBreakdown:
    r"""A granular breakdown of a trade.

    This includes information relating to fees and slippage.
    """

    without_fee_or_slippage: float
    with_fee: float
    without_fee: float
    fee: float


@freezable(frozen=True, no_new_attribs=True)
@dataclass
class TradeResult:
    r"""The result of performing a trade.

    This includes granular information about the trade details,
    including the amount of fees collected and the total delta.
    Additionally, breakdowns for the updates that should be applied
    to the user and the market are computed.
    """

    user_result: AgentTradeResult
    market_result: MarketTradeResult
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
