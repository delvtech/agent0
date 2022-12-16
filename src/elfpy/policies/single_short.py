"""
User strategy that opens a single short and doesn't close until liquidation
"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments

from elfpy.agent import Agent
from elfpy.markets import Market
from elfpy.pricing_models.base import PricingModel
from elfpy.types import MarketActionType


class Policy(Agent):
    """simple short thatonly has one long open at a time"""

    def __init__(self, wallet_address, budget=100):
        """call basic policy init then add custom stuff"""
        self.pt_to_short = 100
        super().__init__(wallet_address, budget)

    def action(self, market: Market, pricing_model: PricingModel):
        """
        implement user strategy
        short if you can, only once
        """
        action_list = []
        block_position_list = list(self.wallet.token_in_protocol.values())
        has_opened_short = bool(any((x < -1 for x in block_position_list)))
        can_open_short = self.get_max_pt_short(market, pricing_model) >= self.pt_to_short
        if can_open_short and not has_opened_short:
            action_list.append(
                self.create_agent_action(action_type=MarketActionType.OPEN_SHORT, trade_amount=self.pt_to_short)
            )
        return action_list
