"""
User strategy that adds base liquidity and doesn't remove until liquidation
"""
# TODO: the init calls are replicated across each strategy, which looks like duplicate code
#     this should be resolved once we fix user inheritance
# pylint: disable=duplicate-code

from elfpy.strategies.basic import BasicPolicy


class Policy(BasicPolicy):
    """
    simple LP
    only has one LP open at a time
    """

    def __init__(self, market, rng, wallet_address, budget=1000, verbose=None, amount_to_lp=100):
        """call basic policy init then add custom stuff"""
        self.amount_to_lp = amount_to_lp
        self.is_lp = True
        self.is_shorter = False
        super().__init__(
            market=market,
            rng=rng,
            wallet_address=wallet_address,
            budget=budget,
            verbose=verbose,
        )

    def action(self):
        """
        implement user strategy
        LP if you can, but only do it once
        """
        action_list = []
        # print(f" evaluating whether to LP: {self.can_lp} and {self.has_lp}")
        if self.can_lp and not self.has_lp:
            action_list.append(self.create_agent_action(action_type="add_liquidity", trade_amount=self.amount_to_lp))
        return action_list
