"""
Special reserved user strategy that is used to initialize a market with a desired amount of share & bond reserves
"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments

from elfpy.agent import Agent
from elfpy.markets import Market
from elfpy.pricing_models import PricingModel, ElementPricingModel, HyperdrivePricingModel


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

    def action(self, market: Market, pricing_model: PricingModel):
        """
        implement user strategy
        LP if you can, but only do it once
        short if you can, but only do it once
        TODO: FIXME: actions should receive market_state, pricing_model, and world_state
        """
        has_lp = self.wallet.lp_in_wallet > 0
        if has_lp:
            action_list = []
        else:
            if pricing_model.model_name() == HyperdrivePricingModel().model_name():
                action_list = [
                    self.create_agent_action(action_type="add_liquidity", trade_amount=self.first_base_to_lp),
                    self.create_agent_action(action_type="open_short", trade_amount=self.pt_to_short),
                    self.create_agent_action(action_type="add_liquidity", trade_amount=self.second_base_to_lp),
                ]
            else:
                raise ValueError(f"Pricing model = {pricing_model.model_name} is not supported.")
        return action_list
