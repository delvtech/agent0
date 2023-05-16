"""Base policy class

Policies inherit from Users (thus each policy is assigned to a user)
subclasses of BasicPolicy will implement trade actions
"""
from __future__ import annotations  # types will be strings by default in 3.11

from typing import TYPE_CHECKING

import elfpy.agents.agent as elf_agent
import elfpy.types as types

if TYPE_CHECKING:
    import elfpy.markets.hyperdrive.hyperdrive_market as hyperdrive_market


class Policy(elf_agent.Agent):
    """Most basic policy setup, which implements a noop agent that performs no action"""

    def action(self, market: hyperdrive_market.Market) -> list[types.Trade]:
        """Returns an empty list, indicating now action"""
        # pylint disable=unused-argument
        return []


class NoActionAgent(elf_agent.AgentFP):
    """Most basic policy setup, which implements a noop agent that performs no action"""

    def action(self, market: hyperdrive_market.MarketFP) -> list[types.Trade]:
        """Returns an empty list, indicating now action"""
        # pylint disable=unused-argument
        return []
