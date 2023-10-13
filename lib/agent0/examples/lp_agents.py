"""Script to showcase running default implemented agents."""
from __future__ import annotations

import logging
import os

from agent0 import initialize_accounts
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import run_agents
from agent0.hyperdrive.policies import Zoo
from agent0.utilities import check_docker

# from ethpy.hyperdrive import fetch_hyperdrive_address_from_uri
from eth_typing import URI
from ethpy import EthConfig
from ethpy.eth_config import build_eth_config
from fixedpointmath import FixedPoint

# Define the unique env filename to use for this script
ENV_FILE = "lp_agents.account.env"
# Host of docker services
HOST = "localhost"
# Username binding of bots
USERNAME = "changeme"
# Run this file with this flag set to true to close out all open positions
LIQUIDATE = False
RESTART_DOCKER = True
BUDGET = 1_000_000  # 1 milly

os.environ["DEVELOP"] = "true"

# we're in develop mode, so we'll get a new env file made for us
if os.path.exists(ENV_FILE):
    os.remove(ENV_FILE)

check_docker(restart=True)

# Build configuration
eth_config = EthConfig(artifacts_uri=f"http://{HOST}:8080", rpc_uri=f"http://{HOST}:8545")

env_config = EnvironmentConfig(
    delete_previous_logs=True,
    halt_on_errors=True,
    log_formatter="%(message)s",
    log_filename="agent0-logs",
    log_level=logging.INFO,
    log_stdout=True,
    random_seed=1234,
    database_api_uri=f"http://{HOST}:5002",
    username=USERNAME,
)

agent_config: list[AgentConfig] = [
    AgentConfig(
        name="LPandArb",
        policy=Zoo.LPandArb,
        number_of_agents=1,
        slippage_tolerance=None,  # No slippage tolerance for arb bot
        # Fixed budgets
        base_budget_wei=FixedPoint(BUDGET).scaled_value,
        eth_budget_wei=FixedPoint(1).scaled_value,
        policy_config=Zoo.LPandArb.Config(
            lp_portion=FixedPoint("0.5"),  # LP with 50% of capital
            high_fixed_rate_thresh=FixedPoint(0.051),  # Upper fixed rate threshold
            low_fixed_rate_thresh=FixedPoint(0.049),  # Lower fixed rate threshold
        ),
    ),
    AgentConfig(
        name="Random",
        policy=Zoo.random,
        number_of_agents=1,
        slippage_tolerance=None,
        # Fixed budget
        base_budget_wei=FixedPoint(BUDGET / 2).scaled_value,  # 100k base
        eth_budget_wei=FixedPoint(1).scaled_value,
        policy_config=Zoo.random.Config(trade_chance=FixedPoint("0.1")),
    ),
    AgentConfig(
        name="JustArb",
        policy=Zoo.arbitrage,
        number_of_agents=0,
        slippage_tolerance=None,
        # Fixed budget
        base_budget_wei=FixedPoint(BUDGET).scaled_value,
        eth_budget_wei=FixedPoint(1).scaled_value,
        policy_config=Zoo.arbitrage.Config(
            trade_amount=FixedPoint(BUDGET * 0.1),  # Open 1k in base or short 1k bonds
            high_fixed_rate_thresh=FixedPoint(0.06),  # Upper fixed rate threshold
            low_fixed_rate_thresh=FixedPoint(0.04),  # Lower fixed rate threshold
        ),
    ),
]

# not needed unless you're interacting directly with the smart contract, outside of the bot framework
# addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))

# Build accounts env var
# This function writes a user defined env file location.
# If it doesn't exist, create it based on agent_config
# (If os.environ["DEVELOP"] is False, will clean exit and print instructions on how to fund agent)
# If it does exist, read it in and use it
account_key_config = initialize_accounts(agent_config, env_file=ENV_FILE, random_seed=env_config.random_seed)
eth_config = build_eth_config()
eth_config.rpc_uri = URI("http://localhost:8546")

# Run agents
run_agents(
    env_config,
    agent_config,
    account_key_config,
    eth_config=eth_config,
    liquidate=LIQUIDATE,
)
