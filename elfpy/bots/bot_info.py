"""Information for creating a bot"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from elfpy.agents.policies.base import BasePolicy

from .budget import Budget


@dataclass
class BotInfo:
    """Information about a bot

    Attributes
    ----------
    name : str
        The name of the agent
    policy : str
        The agent's policy; should match the class name
    number_of_bots : int
        The number of bots of this type to spin up
    trade_chance : float
        Percent chance that a agent gets to trade on a given block
    budget : Budget
        The budget for the agent
    scratch : dict
        Any parameters for custom bots should go here
    """

    policy: Type[BasePolicy]  # TODO: Delete this when we remove evm_bots
    index: int | None = None  # TODO: Make this required when we remove evm_bots
    name: str = "BoringBotty"
    policy_str: str = "NoActionPolicy"  # TODO: Rename to `policy` when we remove evm_bots
    budget: Budget = Budget()
    number_of_bots: int = 1
    trade_chance: float = 0.8
    init_kwargs: dict = {}
