"""Information for creating a bot."""
from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass
from typing import Type

from elfpy.agents.policies.base import BasePolicy


# FIXME: Do we need this or can get combine with the Agent class?  I submit that we can.
@dataclass
class BotInfo:
    """Information about a bot.
    Attributes
    ----------
    policy : Type[Agent]
        The agent's policy.
    trade_chance : float
        Percent chance that a agent gets to trade on a given block.
    risk_threshold : float | None
        The risk threshold for the agent.
    budget : Budget[mean, std, min, max]
        The budget for the agent.
    risk : Risk[mean, std, min, max]
        The risk for the agent.
    index : int | None
        The index of the agent in the list of ALL agents.
    name : str
        The name of the agent.
    """

    Budget = namedtuple("Budget", ["mean", "std", "min", "max"])
    Risk = namedtuple("Risk", ["mean", "std", "min", "max"])
    policy: Type[BasePolicy]
    trade_chance: float = 0.1
    risk_threshold: float | None = None
    budget: Budget = Budget(mean=5_000, std=2_000, min=1_000, max=10_000)
    risk: Risk = Risk(mean=0.02, std=0.01, min=0.0, max=0.06)
    index: int | None = None
    name: str = "botty mcbotface"

    def __repr__(self) -> str:
        """Return a string representation of the object."""
        return f"{self.name} " + ",".join(
            [f"{key}={value}" if value else "" for key, value in self.__dict__.items() if key not in ["name", "policy"]]
        )
