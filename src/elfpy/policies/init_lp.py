"""
Special reserved user strategy that is used to initialize a market with a desired amount of share & bond reserves
"""
# pylint: disable=duplicate-code
# pylint: disable=too-many-arguments

from elfpy.policies.basic import BasicPolicy
from elfpy.markets import Market
from elfpy.pricing_models import PricingModel, ElementPricingModel, HyperdrivePricingModel


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(
        self,
        wallet_address,
        budget=1000,
        base_to_lp=100,
        pt_to_short=100,
    ):
        """call basic policy init then add custom stuff"""
        self.base_to_lp = base_to_lp
        self.pt_to_short = pt_to_short
        super().__init__(wallet_address, budget)

    def action(self, market: Market, pricing_model: PricingModel):
        """
        implement user strategy
        LP if you can, but only do it once
        short if you can, but only do it once
        """
        has_lp = self.wallet.lp_in_wallet > 0
        if has_lp:
            action_list = []
        else:
            if pricing_model.model_name() == ElementPricingModel().model_name():
                # TODO: This doesn't work correctly -- need to add PT
                action_list = [
                    self.create_agent_action(action_type="add_liquidity", trade_amount=self.base_to_lp),
                ]
            elif pricing_model.model_name() == HyperdrivePricingModel().model_name():
                action_list = [
                    self.create_agent_action(action_type="add_liquidity", trade_amount=self.base_to_lp),
                    self.create_agent_action(action_type="open_short", trade_amount=self.pt_to_short),
                ]
            else:
                raise ValueError(f"Pricing model = {pricing_model.model_name} is not supported.")
        return action_list
