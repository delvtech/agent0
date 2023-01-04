"""
Special reserved user strategy that is used to initialize a market with a desired amount of share & bond reserves
"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments

from elfpy.agent import Agent
from elfpy.markets import Market
from elfpy.pricing_models.base import PricingModel
from elfpy.pricing_models.hyperdrive import HyperdrivePricingModel
from elfpy.pricing_models.yieldspace import YieldSpacePricingModel
from elfpy.types import MarketActionType


class Policy(Agent):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(
        self,
        wallet_address,
        budget=1000,
        first_base_to_lp=1,
        pt_to_short=100,
        second_base_to_lp=100,
    ):
        """call basic policy init then add custom stuff"""
        self.first_base_to_lp = first_base_to_lp
        self.pt_to_short = pt_to_short
        self.second_base_to_lp = second_base_to_lp
        super().__init__(wallet_address, budget)

    def action(self, _market: Market, pricing_model: PricingModel):
        """
        implement user strategy
        LP if you can, but only do it once
        short if you can, but only do it once
        """
        has_lp = self.wallet.lp_tokens > 0
        if has_lp:
            action_list = []
        else:
            if pricing_model.model_name() == HyperdrivePricingModel().model_name():
                # TODO: This PM fails the tests
                action_list = [
                    self.create_agent_action(
                        action_type=MarketActionType.ADD_LIQUIDITY, trade_amount=self.first_base_to_lp
                    ),
                    self.create_agent_action(action_type=MarketActionType.OPEN_SHORT, trade_amount=self.pt_to_short),
                    self.create_agent_action(
                        action_type=MarketActionType.ADD_LIQUIDITY, trade_amount=self.second_base_to_lp
                    ),
                ]
            elif pricing_model.model_name() == YieldSpacePricingModel().model_name():
                action_list = [
                    self.create_agent_action(
                        action_type=MarketActionType.ADD_LIQUIDITY, trade_amount=self.first_base_to_lp
                    ),
                    self.create_agent_action(action_type=MarketActionType.OPEN_SHORT, trade_amount=self.pt_to_short),
                    self.create_agent_action(
                        action_type=MarketActionType.ADD_LIQUIDITY, trade_amount=self.second_base_to_lp
                    ),
                ]
            else:
                raise ValueError(f"Pricing model = {pricing_model.model_name()} is not supported.")
        return action_list
