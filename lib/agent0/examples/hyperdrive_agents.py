"""Script to showcase running default implemented agents"""
from __future__ import annotations

import logging

from agent0 import initialize_accounts
from agent0.base.config import AgentConfig, Budget, EnvironmentConfig
from agent0.hyperdrive.exec import run_agents
from agent0.hyperdrive.policies import Policies
from ethpy import EthConfig
from fixedpointmath import FixedPoint

# Define the unique env filename to use for this script
ENV_FILE = "hyperdrive_agents.account.env"
# Host of docker services
HOST = "localhost"
# Username binding of bots
USERNAME = "changeme"

eth_config = EthConfig(artifacts_uri="http://" + HOST + ":8080", rpc_uri="http://" + HOST + ":8545")

env_config = EnvironmentConfig(
    delete_previous_logs=False,
    halt_on_errors=True,
    log_filename="agent0-logs",
    log_level=logging.INFO,
    log_stdout=True,
    random_seed=1234,
    database_api_uri="http://" + HOST + ":5002",
    username=USERNAME,
)

agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=Policies.random_agent,
        number_of_agents=3,
        slippage_tolerance=FixedPoint("0.0001"),
        base_budget_wei=Budget(
            mean_wei=FixedPoint(5_000).scaled_value,  # 5k base
            std_wei=FixedPoint(1_000).scaled_value,  # 1k base
            min_wei=1,  # 1 WEI base
            max_wei=FixedPoint(100_000).scaled_value,  # 100k base
        ),
        eth_budget_wei=Budget(min_wei=FixedPoint(1).scaled_value, max_wei=FixedPoint(1).scaled_value),
        init_kwargs={"trade_chance": FixedPoint("0.8")},
    ),
]


# Build accounts env var
# This function writes a user defined env file location.
# If it doesn't exist, create it based on agent_config
# (If develop is False, will clean exit and print instructions on how to fund agent)
# If it does exist, read it in and use it
account_key_config = initialize_accounts(agent_config, env_file=ENV_FILE, random_seed=env_config.random_seed)

# Run agents
run_agents(env_config, agent_config, account_key_config, eth_config=eth_config)
