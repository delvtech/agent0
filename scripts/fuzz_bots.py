"""Runs random bots against the local chain for fuzz testing"""

from __future__ import annotations

import logging
import os
import random
import sys
import time

import numpy as np
from eth_typing import BlockNumber
from fixedpointmath import FixedPoint
from web3.types import RPCEndpoint

from agent0.chainsync.db.api import balance_of
from agent0.core import initialize_accounts
from agent0.core.base import Quantity, TokenType
from agent0.core.base.config import AgentConfig, EnvironmentConfig
from agent0.core.hyperdrive.agent import build_wallet_positions_from_chain, build_wallet_positions_from_db
from agent0.core.hyperdrive.crash_report import setup_hyperdrive_crash_report_logging
from agent0.core.hyperdrive.policies import PolicyZoo
from agent0.core.hyperdrive.utilities.run_bots import (
    async_fund_agents_with_fake_user,
    get_agent_accounts,
    trade_if_new_block,
)
from agent0.ethpy import build_eth_config
from agent0.ethpy.hyperdrive import HyperdriveReadWriteInterface, fetch_hyperdrive_address_from_uri
from agent0.hyperlogs import setup_logging
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar

FUND_RETRY_COUNT = 5
DEFAULT_READ_RETRY_COUNT = 5

STOP_CHAIN_ON_CRASH = False

# NOTE be sure to adjust `eth.env` to connect to a specific chain

# Define the unique env filename to use for this script
ACCOUNT_ENV_FILE = "fuzz_test_bots.account.env"
# Username binding of bots
USERNAME = "test_bots"
# The amount of base token each bot receives
# We don't have access to the pool liquidity here,
# but we assume this is enough base to make trades that are at the pool's max
BASE_BUDGET_PER_BOT = FixedPoint(10_000_000)
ETH_BUDGET_PER_BOT = FixedPoint(1_000)
# The slippage tolerance for trades
SLIPPAGE_TOLERANCE = FixedPoint("0.01")  # 1% slippage
# Run this file with this flag set to true to close out all open positions
LIQUIDATE = False
# Retry latency & exponential backoff
START_LATENCY = 1
BACKOFF = 2

# Make sure the bots have at least 10% of their budget after each trade
minimum_avg_agent_base = BASE_BUDGET_PER_BOT / FixedPoint(10)

log_to_rollbar = initialize_rollbar("localfuzzbots")

# Build configuration
env_config = EnvironmentConfig(
    delete_previous_logs=True,
    halt_on_errors=not LIQUIDATE,
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

global_rng = np.random.default_rng(env_config.global_random_seed)
setup_logging(
    log_filename=env_config.log_filename,
    max_bytes=env_config.max_bytes,
    log_level=env_config.log_level,
    delete_previous_logs=env_config.delete_previous_logs,
    log_stdout=env_config.log_stdout,
    log_format_string=env_config.log_formatter,
)
setup_hyperdrive_crash_report_logging()

agent_config: list[AgentConfig] = [
    AgentConfig(
        policy=PolicyZoo.random,
        number_of_agents=2,
        # Fixed budget
        base_budget_wei=BASE_BUDGET_PER_BOT.scaled_value,
        eth_budget_wei=ETH_BUDGET_PER_BOT.scaled_value,
        policy_config=PolicyZoo.random.Config(
            slippage_tolerance=SLIPPAGE_TOLERANCE,
            trade_chance=FixedPoint("0.8"),
            randomly_ignore_slippage_tolerance=True,
        ),
    ),
    AgentConfig(
        policy=PolicyZoo.random_hold,
        number_of_agents=2,
        # Fixed budget
        base_budget_wei=BASE_BUDGET_PER_BOT.scaled_value,
        eth_budget_wei=ETH_BUDGET_PER_BOT.scaled_value,
        policy_config=PolicyZoo.random_hold.Config(
            slippage_tolerance=SLIPPAGE_TOLERANCE,
            trade_chance=FixedPoint("0.8"),
            randomly_ignore_slippage_tolerance=True,
            max_open_positions=2000,
        ),
    ),
]


# Build accounts env var
# This function writes a user defined env file location.
# If it doesn't exist, create it based on agent_config
# (If os.environ["DEVELOP"] is False, will clean exit and print instructions on how to fund agent)
# If it does exist, read it in and use it
account_key_config = initialize_accounts(
    agent_config, env_file=ACCOUNT_ENV_FILE, random_seed=env_config.global_random_seed
)


# Get config and addresses
eth_config = build_eth_config(dotenv_file="eth.env")
contract_addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))

# Build the interface object
interface = HyperdriveReadWriteInterface(
    eth_config,
    contract_addresses,
    read_retry_count=env_config.read_retry_count,
    write_retry_count=env_config.write_retry_count,
)

# Run agents
# If bots crash, we use an RPC to stop mining anvil
try:
    async_fund_agents_with_fake_user(interface, account_key_config)

    # Construct agent objects from env keys
    agent_accounts = get_agent_accounts(
        interface,
        agent_config,
        account_key_config,
        global_rng,
    )
    wallet_addrs = [str(agent.checksum_address) for agent in agent_accounts]

    # Load existing wallet balances
    if eth_config.database_api_uri is not None:
        # Get existing open positions from db api server
        balances = balance_of(eth_config.database_api_uri, wallet_addrs)
        # Set balances of wallets based on db and chain
        for agent in agent_accounts:
            # TODO is this the right location for this to happen?
            # On one hand, doing it here makes sense because parameters such as db uri doesn't have to
            # be passed in down all the function calls when wallets are initialized.
            # On the other hand, we initialize empty wallets just to overwrite here.
            # Keeping here for now for later discussion
            agent.wallet = build_wallet_positions_from_db(
                agent.checksum_address, balances, interface.base_token_contract
            )
    else:
        for agent in agent_accounts:
            agent.wallet = build_wallet_positions_from_chain(
                agent.checksum_address, interface.hyperdrive_contract, interface.base_token_contract
            )

    last_executed_block = BlockNumber(0)
    poll_latency = START_LATENCY + random.uniform(0, 1)
    while True:
        # Check if all agents done trading
        # If so, exit cleanly
        # The done trading state variable gets set internally
        if all(agent.done_trading for agent in agent_accounts):
            break
        new_executed_block = trade_if_new_block(
            interface,
            agent_accounts,
            env_config.halt_on_errors,
            env_config.halt_on_slippage,
            env_config.crash_report_to_file,
            env_config.crash_report_file_prefix,
            env_config.log_to_rollbar,
            last_executed_block,
            LIQUIDATE,
            env_config.randomize_liquidation,
        )
        if minimum_avg_agent_base is not None:
            if (
                sum(agent.wallet.balance.amount for agent in agent_accounts) / FixedPoint(len(agent_accounts))
                < minimum_avg_agent_base
            ):
                async_fund_agents_with_fake_user(interface, account_key_config)
                # Update agent accounts with new wallet balances
                for agent in agent_accounts:
                    # Contract call to get base balance
                    (_, base_amount) = interface.get_eth_base_balances(agent)
                    base_obj = Quantity(amount=base_amount, unit=TokenType.BASE)
                    agent.wallet.balance = base_obj
        if new_executed_block == last_executed_block:
            # wait
            time.sleep(poll_latency)
            poll_latency *= BACKOFF
            poll_latency += random.uniform(0, 1)
        else:
            # Reset backoff
            poll_latency = START_LATENCY + random.uniform(0, 1)

# Don't stop chain if the user interrupts
except KeyboardInterrupt:
    sys.exit()
except Exception as exc:  # pylint: disable=broad-exception-caught
    # create hyperdrive interface object
    if STOP_CHAIN_ON_CRASH:
        interface.web3.provider.make_request(method=RPCEndpoint("evm_setIntervalMining"), params=[0])
    raise exc
