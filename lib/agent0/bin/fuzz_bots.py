"""Runs random bots against the local chain for fuzz testing"""
from __future__ import annotations

import logging
import random
import sys

import rollbar
from ethpy.hyperdrive.interface import HyperdriveInterface
from fixedpointmath import FixedPoint
from hyperlogs.rollbar_utilities import initialize_rollbar
from web3.types import RPCEndpoint

from agent0 import initialize_accounts
from agent0.base.config import AgentConfig, EnvironmentConfig
from agent0.hyperdrive.exec import setup_and_run_agent_loop
from agent0.hyperdrive.policies import Zoo

STOP_CHAIN_ON_CRASH = False

# NOTE be sure to adjust `eth.env` to connect to a specific chain

# Define the unique env filename to use for this script
ENV_FILE = "fuzz_test_bots.account.env"
# Username binding of bots
USERNAME = "test_bots"
# The amount of base token each bot receives
BASE_BUDGET_PER_BOT = FixedPoint(1000)
ETH_BUDGET_PER_BOT = FixedPoint(10)
# The slippage tolerance for trades
SLIPPAGE_TOLERANCE = FixedPoint("0.0001")  # 0.1% slippage
# Run this file with this flag set to true to close out all open positions
LIQUIDATE = False

log_to_rollbar = initialize_rollbar("localfuzzbots")

# Build configuration
env_config = EnvironmentConfig(
    delete_previous_logs=True,
    halt_on_errors=False,
    crash_report_to_file=True,
    crash_report_file_prefix="fuzz_bots",
    log_filename=".logging/debug_bots.log",
    log_level=logging.CRITICAL,
    log_to_rollbar=log_to_rollbar,
    log_stdout=True,
    # TODO this should be able to accept None to allow for random
    global_random_seed=random.randint(0, 10000000),
    username=USERNAME,
    # Fuzz bots retries smart contract transactions 3 times
    write_retry_count=3,
)

agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=Zoo.random,
        number_of_agents=3,
        # Fixed budget
        base_budget_wei=BASE_BUDGET_PER_BOT.scaled_value,
        eth_budget_wei=ETH_BUDGET_PER_BOT.scaled_value,
        policy_config=Zoo.random.Config(
            slippage_tolerance=SLIPPAGE_TOLERANCE,
            trade_chance=FixedPoint("0.8"),
        ),
    ),
]


# Build accounts env var
# This function writes a user defined env file location.
# If it doesn't exist, create it based on agent_config
# (If os.environ["DEVELOP"] is False, will clean exit and print instructions on how to fund agent)
# If it does exist, read it in and use it
account_key_config = initialize_accounts(agent_config, env_file=ENV_FILE, random_seed=env_config.global_random_seed)

# Run agents
# If bots crash, we use an RPC to stop mining anvil
try:
    minimum_avg_agent_base = BASE_BUDGET_PER_BOT / FixedPoint(10)
    setup_and_run_agent_loop(
        env_config, agent_config, account_key_config, liquidate=LIQUIDATE, minimum_avg_agent_base=minimum_avg_agent_base
    )
# Don't stop chain if the user interrupts
except KeyboardInterrupt:
    sys.exit()
except Exception as exc:  # pylint: disable=broad-exception-caught
    # create hyperdrive interface object
    if STOP_CHAIN_ON_CRASH:
        hyperdrive = HyperdriveInterface()
        hyperdrive.web3.provider.make_request(method=RPCEndpoint("evm_setIntervalMining"), params=[0])
    if log_to_rollbar:
        rollbar.report_exc_info(sys.exc_info())
    raise exc
