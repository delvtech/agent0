"""Script to showcase running default implemented agents."""
from __future__ import annotations

import logging

from agent0 import initialize_accounts
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import run_agents
from agent0.hyperdrive.policies import Zoo
from fixedpointmath import FixedPoint

# NOTE be sure to adjust `eth.env` to connect to a specific chain

# Define the unique env filename to use for this script
ENV_FILE = "hyperdrive_agents.account.env"
# Username binding of bots
USERNAME = "changeme"
# The amount of base token each bot receives
BASE_BUDGET_PER_BOT = FixedPoint(50).scaled_value  # 50 base in wei
ETH_BUDGET_PER_BOT = FixedPoint(1).scaled_value  # 1 eth in wei
# The slippage tolerance for trades
SLIPPAGE_TOLERANCE = FixedPoint("0.0001")  # 0.1% slippage
# Run this file with this flag set to true to close out all open positions
LIQUIDATE = False

# Build configuration
env_config = EnvironmentConfig(
    delete_previous_logs=True,
    halt_on_errors=False,
    log_filename=".logging/agent0_logs.log",
    log_level=logging.CRITICAL,
    log_stdout=True,
    random_seed=1234,
    username=USERNAME,
)

agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=Zoo.arbitrage,
        number_of_agents=0,
        slippage_tolerance=SLIPPAGE_TOLERANCE,  # No slippage tolerance for arb bot
        # Fixed budgets
        base_budget_wei=BASE_BUDGET_PER_BOT,
        eth_budget_wei=ETH_BUDGET_PER_BOT,
        policy_config=Zoo.arbitrage.Config(
            trade_amount=FixedPoint(10),  # Open 10 base or short 10 bonds
            high_fixed_rate_thresh=FixedPoint(0.1),  # Upper fixed rate threshold
            low_fixed_rate_thresh=FixedPoint(0.02),  # Lower fixed rate threshold
        ),
    ),
    AgentConfig(
        policy=Zoo.random,
        number_of_agents=0,
        slippage_tolerance=SLIPPAGE_TOLERANCE,
        # Fixed budget
        base_budget_wei=BASE_BUDGET_PER_BOT,
        eth_budget_wei=ETH_BUDGET_PER_BOT,
        policy_config=Zoo.random.Config(trade_chance=FixedPoint("0.8")),
    ),
]


# Build accounts env var
# This function writes a user defined env file location.
# If it doesn't exist, create it based on agent_config
# (If develop is False, will clean exit and print instructions on how to fund agent)
# If it does exist, read it in and use it
account_key_config = initialize_accounts(agent_config, env_file=ENV_FILE, random_seed=env_config.random_seed)

# Run agents
run_agents(env_config, agent_config, account_key_config, liquidate=LIQUIDATE)
