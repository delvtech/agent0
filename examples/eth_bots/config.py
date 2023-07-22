"""Experiment configuration"""
from __future__ import annotations

import logging

from fixedpointmath import FixedPoint

from elfpy.agents.policies import Policies
from elfpy.bots import BotInfo, Budget, EnvironmentConfig

# You can import custom policies here. For example:
from .custom_policies.example_custom_policy import ExampleCustomPolicy

agent_config: list[BotInfo] = [
    BotInfo(
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
    BotInfo(
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
    BotInfo(
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
    BotInfo(
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
    hostname="http://localhost",
    artifacts_port="80",
    rpc_port="8545",
    user_registry_port="5002",
    username="changeme",
)
