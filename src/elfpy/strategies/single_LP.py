# pylint: disable=duplicate-code

from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, market, rng, wallet_address, verbose=None, budget=1000, amount_to_LP=100):
        """call basic policy init then add custom stuff"""
        super().__init__(market=market, rng=rng, wallet_address=wallet_address, verbose=verbose, budget=budget, amount_to_LP=amount_to_LP) 

    def action(self):
        """
        implement user strategy
        LP if you can, but only do it once
        """
        action_list = []
        if not self.has_LPd and self.can_LP:
            action_list.append(self.create_agent_action(action_type="add_liquidity", trade_amount=self.amount_to_LP))
        return action_list
