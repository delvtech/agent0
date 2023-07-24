"""Information for creating a bot"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from elfpy.agents.policies.base import BasePolicy

from .budget import Budget


@dataclass
class AgentConfig:
    """Information about a bot

    Attributes
    ----------
    policy : str
        The agent's policy; should match the class name
    name : str
        The name of the agent
    budget : Budget
        The budget for the agent
    number_of_agents : int
        The number of bots of this type to spin up
    init_kwargs : dict
        A dictionary of keyword arguments for the policy constructor
    """

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    policy: Type[BasePolicy]
    name: str = "BoringBotty"
    budget: Budget = Budget()
    number_of_agents: int = 1
    init_kwargs: dict = field(default_factory=dict)
