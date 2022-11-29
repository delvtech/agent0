# pylint: disable=duplicate-code

from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, market, rng, wallet_address, budget=1000, verbose=None, amount_to_LP=100):
        """call basic policy init then add custom stuff"""
        super().__init__(market=market, rng=rng, wallet_address=wallet_address, budget=budget, verbose=verbose, amount_to_LP=amount_to_LP) 

    def action(self):
        """
        implement user strategy
        LP if you can, but only do it once
        """
        action_list = []
        # print(f" evaluating whether to LP: {self.can_LP} and {self.has_LPd}")
        if self.can_LP and not self.has_LPd:
            action_list.append(self.create_agent_action(action_type="add_liquidity", trade_amount=self.amount_to_LP))
        return action_list
