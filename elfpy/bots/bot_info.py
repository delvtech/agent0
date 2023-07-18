"""Information for creating a bot"""
from __future__ import annotations

from collections import namedtuple
from dataclasses import dataclass, field

from elfpy.agents.policies.base import BasePolicy

from .budget import Budget


@dataclass
class BotInfo:  # TODO: Rename to `BotConfig` when we remove evm_bots
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

    # TODO: We should be able to enable this again once we remove evm_bots
    # pylint: disable=to-many-instance-attributes

    policy: BasePolicy
    index: int | None = None  # TODO: Make this required when we remove evm_bots
    name: str = "BoringBotty"
    budget: Budget = Budget()
    number_of_bots: int = 1
    init_kwargs: dict = field(default_factory=dict)
    # TODO: Remove below once we remove evm_bots
    trade_chance: float = 0.8
    risk_threshold: float = 0.8
    Risk = namedtuple("Risk", ["mean", "std", "min", "max"])
    risk: Risk = Risk(mean=0.02, std=0.01, min=0.0, max=0.06)
