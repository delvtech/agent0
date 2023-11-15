"""Runs random bots against the local chain for fuzz testing"""
from __future__ import annotations

import logging
import random
import sys

from agent0 import initialize_accounts
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import run_agents
from agent0.hyperdrive.policies import Zoo
from ethpy.hyperdrive.api import HyperdriveInterface
from fixedpointmath import FixedPoint
from web3.types import RPCEndpoint

STOP_CHAIN_ON_CRASH = False

# NOTE be sure to adjust `eth.env` to connect to a specific chain

# Define the unique env filename to use for this script
ENV_FILE = "fuzz_test_bots.account.env"
# Username binding of bots
USERNAME = "test_bots"
# The amount of base token each bot receives
BASE_BUDGET_PER_BOT = FixedPoint(100).scaled_value  # 50 base in wei
ETH_BUDGET_PER_BOT = FixedPoint(10).scaled_value  # 1 eth in wei
# The slippage tolerance for trades
SLIPPAGE_TOLERANCE = FixedPoint("0.0001")  # 0.1% slippage
# Run this file with this flag set to true to close out all open positions
LIQUIDATE = False

# Build configuration
env_config = EnvironmentConfig(
    delete_previous_logs=True,
    halt_on_errors=True,
    crash_report_to_file=True,
    log_filename=".logging/debug_bots.log",
    log_level=logging.CRITICAL,
    log_stdout=True,
    # TODO this should be able to accept None to allow for random
    random_seed=random.randint(0, 10000000),
    username=USERNAME,
)

agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=Zoo.random,
        number_of_agents=3,
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
# (If os.environ["DEVELOP"] is False, will clean exit and print instructions on how to fund agent)
# If it does exist, read it in and use it
account_key_config = initialize_accounts(agent_config, env_file=ENV_FILE, random_seed=env_config.random_seed)

# Run agents
# If bots crash, we use an RPC to stop mining anvil
try:
    run_agents(env_config, agent_config, account_key_config, liquidate=LIQUIDATE)
# Don't stop chain if the user interrupts
except KeyboardInterrupt:
    sys.exit()
except Exception as exc:  # pylint: disable=broad-exception-caught
    # create hyperdrive interface object
    if STOP_CHAIN_ON_CRASH:
        hyperdrive = HyperdriveInterface()
        hyperdrive.web3.provider.make_request(method=RPCEndpoint("evm_setIntervalMining"), params=[0])
    raise exc
