"""
Base policy class

Policies inherit from Users (thus each policy is assigned to a user)
subclasses of BasicPolicy will implement trade actions
"""

from elfpy.user import User


class BasicPolicy(User):
    """
    most basic policy setup
    """

    def __init__(self, market, rng, wallet_address, budget, verbose):
        """call basic policy init then add custom stuff"""
        super().__init__(market, rng, wallet_address, budget, verbose)

    def action(self):
        """specify action"""
        action_list = []
        # implement trade here
        return action_list
