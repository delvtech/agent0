"""Information for creating an agent"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Type

from agent0.core.base.policies import BasePolicy

from .budget import Budget


@dataclass
class AgentConfig:
    """Information about an agent."""

    # lots of configs!
    # pylint: disable=too-many-instance-attributes

    policy: Type[BasePolicy]
    """The agent's policy; should match the class name."""
    policy_config: BasePolicy.Config
    """The policy's config object for custom policy configuration."""
    base_budget_wei: Budget | int
    """The base token budget for the agent in units of wei."""
    eth_budget_wei: Budget | int
    """The ethereum budget for the agent in units of wei."""
    number_of_agents: int = 1
    """The number of agents of this type to spin up."""
    private_keys: list[str] | None = None
    """list of strings, where each key contains a private key of one of the agents."""

    def __post_init__(self):
        if self.private_keys is not None and len(self.private_keys) != self.number_of_agents:
            raise ValueError(
                f"if private_keys is set then {len(self.private_keys)=} must equal {self.number_of_agents=}"
            )
