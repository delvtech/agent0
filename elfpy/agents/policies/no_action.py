"""Base policy class

Policies inherit from Users (thus each policy is assigned to a user)
subclasses of BasicPolicy will implement trade actions
"""
from __future__ import annotations  # types will be strings by default in 3.11

import elfpy.markets.base as base
import elfpy.types as types
import elfpy.agents.agent as agent


class NoAction(agent.Agent):
    """
    Most basic policy setup, which implements a noop agent that performs no action
    """

    def action(self, markets: "dict[types.MarketType, base.Market]") -> "list[types.Trade]":
        """Returns an empty list, indicating now action"""
        # pylint disable=unused-argument
        return []
