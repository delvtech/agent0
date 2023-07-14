"""Information for creating a bot"""
from __future__ import annotations

from dataclasses import dataclass

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

    name: str = "botty mcbotface"
    policy: str = "NoActionPolicy"
    number_of_bots: int = 1

    trade_chance: float
    budget: Budget
    scratch: dict

    def __post_init__(self):
        """After init, set index

        index : int | None
            The index of the agent in the list of ALL agents
        """
        self.index = None
