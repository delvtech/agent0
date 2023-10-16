"""Information for creating an agent"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from agent0.base.policies import BasePolicy
from fixedpointmath import FixedPoint

from .budget import Budget


@dataclass
class AgentConfig:
    """Information about an agent

    Attributes
    ----------
    policy : str
        The agent's policy; should match the class name
    name : str
        The name of the agent
    base_budget_wei : Budget | int
        The base token budget for the agent in units of wei
    eth_budget_wei : Budget | int
        The ethereum budget for the agent in units of wei
    number_of_agents : int
        The number of agents of this type to spin up
    private_keys : list[str] | None
        list of strings, where each key contains
    policy_config: BasePolicy.Config | None
        The policy's config object for custom policy configuration
    """

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    policy: Type[BasePolicy]
    name: str = "BoringBotty"
    base_budget_wei: Budget | int = 0
    eth_budget_wei: Budget | int = 0
    slippage_tolerance: FixedPoint | None = FixedPoint("0.0001")  # default to 0.01%
    number_of_agents: int = 1
    private_keys: list[str] | None = None
    # TODO might be able to use default factory for this object for default
    # instead of dong this in the constructor of every policy
    # However, we may just want to explicitly say this field is required
    policy_config: BasePolicy.Config | None = None

    def __post_init__(self):
        if self.private_keys is not None and len(self.private_keys) != self.number_of_agents:
            raise ValueError(
                f"if private_keys is set then {len(self.private_keys)=} must equal {self.number_of_agents=}"
            )
