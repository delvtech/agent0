"""
Base policy class

Policies inherit from Users (thus each policy is assigned to a user)
subclasses of BasicPolicy will implement trade actions
"""

from elfpy.agent import Agent


class BasicPolicy(Agent):
    """
    most basic policy setup
    """

    def action(self):
        """specify action"""
        action_list = []
        # implement trade here
        return action_list
