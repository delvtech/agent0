# pylint: disable=duplicate-code

from elfpy.strategies.basic import BasicPolicy
import numpy as np


class Policy(BasicPolicy):
    """
    simple short
    short until a certain APR is reached
    """

    def __init__(
        self,
        market,
        rng,
        wallet_address,
        budget=1000,
        verbose=None,
        pt_to_short=100,
        short_until_apr=np.inf,
    ):
        """call basic policy init then add custom stuff"""
        self.pt_to_short = pt_to_short
        self.short_until_apr = short_until_apr
        self.is_shorter = True
        self.is_LP = False
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
        short if you can, up to a certain APR (can be infinite)
        """
        action_list = []
        if self.market.rate < self.short_until_apr and self.can_open_short:
            action_list.append(self.create_agent_action(action_type="open_short", trade_amount=self.pt_to_short))
        return action_list
