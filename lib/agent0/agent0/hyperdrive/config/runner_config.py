"""Experiment configuration."""
from __future__ import annotations

import logging

from agent0.base.config import AgentConfig, Budget, EnvironmentConfig
from agent0.hyperdrive.policies import Policies
from fixedpointmath import FixedPoint


def get_default_environment_config() -> EnvironmentConfig:
    """Get the instantiated environment objects

    Returns
    -------
    EnvironmentConfig
        Dataclass containing all of the user environment settings
    """
    return EnvironmentConfig(
        delete_previous_logs=False,
        halt_on_errors=True,
        log_filename="agent0-bots",
        log_level=logging.INFO,
        log_stdout=True,
        random_seed=1234,
        hyperdrive_abi="IHyperdrive",
        base_abi="ERC20Mintable",
        username="changeme",
    )


def get_default_agent_config() -> list[AgentConfig]:
    """Get the instantiated agent config objects

    Returns
    -------
    list[AgentConfig]
        List containing all of the agent specifications
    """
    agent_config: list[AgentConfig] = [
        AgentConfig(
            policy=Policies.random_agent,
            number_of_agents=3,
            slippage_tolerance=FixedPoint(0.0001),
            base_budget=Budget(
                mean_wei=int(5_000e18),  # 5k base
                std_wei=int(1_000e18),  # 1k base
                min_wei=1,  # 1 WEI base
                max_wei=int(100_000e18),  # 100k base
            ),
            eth_budget=Budget(min_wei=int(1e18), max_wei=int(1e18)),
            init_kwargs={"trade_chance": FixedPoint(0.8)},
        ),
        AgentConfig(
            policy=Policies.long_louie,
            number_of_agents=0,
            base_budget=Budget(
                mean_wei=int(5_000e18),  # 5k base
                std_wei=int(1_000e18),  # 1k base
                min_wei=1,  # 1 WEI base
                max_wei=int(100_000e18),  # 100k base
            ),
            eth_budget=Budget(min_wei=int(1e18), max_wei=int(1e18)),
            init_kwargs={"trade_chance": FixedPoint(0.8), "risk_threshold": FixedPoint(0.9)},
        ),
        AgentConfig(
            policy=Policies.short_sally,
            number_of_agents=0,
            base_budget=Budget(
                mean_wei=int(5_000e18),  # 5k base
                std_wei=int(1_000e18),  # 1k base
                min_wei=1,  # 1 WEI base
                max_wei=int(100_000e18),  # 100k base
            ),
            eth_budget=Budget(min_wei=int(1e18), max_wei=int(1e18)),
            init_kwargs={"trade_chance": FixedPoint(0.8), "risk_threshold": FixedPoint(0.8)},
        ),
    ]
    return agent_config
