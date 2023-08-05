"""Information for creating a bot"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Type

from agent0.base.policies import BasePolicy
from fixedpointmath import FixedPoint

from ...hyperdrive.config import Budget


@dataclass
class AgentConfig:
    """Information about a bot

    Attributes
    ----------
    policy : str
        The agent's policy; should match the class name
    name : str
        The name of the agent
    base_budget : Budget
        The base token budget for the agent
    eth_budget : Budget
        The ethereum budget for the agent
    number_of_agents : int
        The number of bots of this type to spin up
    private_keys : list[str] | None
        list of strings, where each key contains
    init_kwargs : dict
        A dictionary of keyword arguments for the policy constructor
    """

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    policy: Type[BasePolicy]
    name: str = "BoringBotty"
    base_budget: Budget = Budget()
    eth_budget: Budget = Budget(min_wei=0, max_wei=0)
    slippage_tolerance: FixedPoint = FixedPoint(0.0001)  # default to 0.01%
    number_of_agents: int = 1
    private_keys: list[str] | None = None
    init_kwargs: dict = field(default_factory=dict)

    def __post_init__(self):
        if self.private_keys is not None and len(self.private_keys) != self.number_of_agents:
            raise ValueError(
                f"if private_keys is set then {len(self.private_keys)=} must equal {self.number_of_agents=}"
            )
