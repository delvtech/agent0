"""
Base policy class

Policies inherit from Users (thus each policy is assigned to a user)
subclasses of BasicPolicy will implement trade actions
"""

from elfpy.markets import Market, MarketAction
from elfpy.pricing_models import PricingModel
from elfpy.agent import Agent


class BasicPolicy(Agent):
    """
    Most basic policy setup, which implements a noop agent that performs no action
    """

    def action(self, market: Market, pricing_model: PricingModel) -> list[MarketAction]:
        """Returns an empty list, indicating now action"""
        # pylint disable=unused-argument
        action_list = []
        return action_list
