"""Experiment configuration."""
from __future__ import annotations

import logging

from fixedpointmath import FixedPoint

from elfpy.agents.policies import Policies
from elfpy.bots import Budget, EnvironmentConfig
from eth_bots.core import AgentConfig

# You can import custom policies here. For example:
from eth_bots.custom_policies.example_custom_policy import ExampleCustomPolicy


def get_eth_bots_config() -> tuple[EnvironmentConfig, list[AgentConfig]]:
    """Get the instantiated config objects for the ETH bots demo.

    Returns
    -------
    tuple[EnvironmentConfig, list[AgentConfig]]
        environment_config : EnvironmentConfig
            Dataclass containing all of the user environment settings
        agent_config : list[BotInfo]
            List containing all of the agent specifications
    """
    environment_config = EnvironmentConfig(
        delete_previous_logs=False,
        halt_on_errors=True,
        log_filename="agent0-bots",
        log_level=logging.INFO,
        log_stdout=True,
        random_seed=1234,
        hyperdrive_abi="IHyperdrive",
        base_abi="ERC20Mintable",
        username_register_url="http://localhost:5002",
        artifacts_url="http://localhost:8080",
        rpc_url="http://localhost:8545",
        username="changeme",
    )

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
        AgentConfig(
            policy=ExampleCustomPolicy,
            number_of_agents=0,
            base_budget=Budget(
                mean_wei=int(1_000e18),  # 1k base
                std_wei=int(100e18),  # 100 base
                min_wei=1,  # 1 WEI base
                max_wei=int(100_000e18),  # 100k base
            ),
            eth_budget=Budget(min_wei=int(1e18), max_wei=int(1e18)),
            init_kwargs={"trade_amount": FixedPoint(100)},
        ),
    ]

    return environment_config, agent_config
