"""Base policy class

Policies inherit from Users (thus each policy is assigned to a user)
subclasses of BasicPolicy will implement trade actions
"""
from __future__ import annotations  # types will be strings by default in 3.11

from typing import List

from elfpy.markets.hyperdrive import Market
from elfpy.agents import Agent
import elfpy.types as types


class NoAction(Agent):
    """
    Most basic policy setup, which implements a noop agent that performs no action
    """

    def action(self, market: Market) -> List[types.Trade]:
        """Returns an empty list, indicating now action"""
        # pylint disable=unused-argument
        return []
