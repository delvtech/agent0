"""Experiment configuration"""
from __future__ import annotations

import logging

from fixedpointmath import FixedPoint

from elfpy.agents.policies import Policies
from elfpy.bots import AgentConfig, Budget, EnvironmentConfig

# You can import custom policies here. For example:
from .custom_policies.example_custom_policy import ExampleCustomPolicy

agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=Policies.random_agent,
        number_of_agents=3,
        budget=Budget(
            mean_wei=int(5_000e18),  # 5k base
            std_wei=int(1_000e18),  # 1k base
            min_wei=1,  # 1 WEI base
            max_wei=int(100_000e18),  # 100k base
        ),
        init_kwargs={"trade_chance": FixedPoint(0.8)},
    ),
    AgentConfig(
        policy=Policies.long_louie,
        number_of_agents=3,
        budget=Budget(
            mean_wei=int(5_000e18),  # 5k base
            std_wei=int(1_000e18),  # 1k base
            min_wei=1,  # 1 WEI base
            max_wei=int(100_000e18),  # 100k base
        ),
        init_kwargs={"trade_chance": FixedPoint(0.8), "risk_threshold": FixedPoint(0.9)},
    ),
    AgentConfig(
        policy=Policies.short_sally,
        number_of_agents=3,
        budget=Budget(
            mean_wei=int(5_000e18),  # 5k base
            std_wei=int(1_000e18),  # 1k base
            min_wei=1,  # 1 WEI base
            max_wei=int(100_000e18),  # 100k base
        ),
        init_kwargs={"trade_chance": FixedPoint(0.8), "risk_threshold": FixedPoint(0.8)},
    ),
    AgentConfig(
        policy=ExampleCustomPolicy,
        number_of_agents=0,
        budget=Budget(
            mean_wei=int(1_000e18),  # 1k base
            std_wei=int(100e18),  # 100 base
            min_wei=1,  # 1 WEI base
            max_wei=int(100_000e18),  # 100k base
        ),
        init_kwargs={"trade_amount": FixedPoint(100)},
    ),
]

environment_config = EnvironmentConfig(
    delete_previous_logs=False,
    halt_on_errors=True,
    log_filename="agent0-bots",
    log_level=logging.INFO,
    log_stdout=True,
    random_seed=1234,
    username_register_url="http://localhost:5002",
    artifacts_url="http://localhost:80",
    rpc_url="http://localhost:8545",
    username="username",
)
