# pylint: disable=duplicate-code

from elfpy.strategies.basic import BasicPolicy
import numpy as np


class Policy(BasicPolicy):
    """
    simple short
    only has one long open at a time
    """

    def __init__(
        self,
        market,
        rng,
        wallet_address,
        budget=100,
        verbose=None,
        pt_to_short=100,
    ):
        """call basic policy init then add custom stuff"""
        self.pt_to_short = pt_to_short
        self.is_LP = False
        self.is_shorter = True
        super().__init__(
            market,
            rng,
            wallet_address,
            budget=budget,
            verbose=verbose
        )

    def action(self):
        """
        implement user strategy
        short if you can, only once
        """
        action_list = []
        if self.can_open_short and not self.has_opened_short:
            action_list.append(self.create_agent_action(action_type="open_short", trade_amount=self.pt_to_short))
        return action_list
