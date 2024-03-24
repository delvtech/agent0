"""Runs random bots against the local chain for fuzz testing"""

from __future__ import annotations

import logging
import random
import sys
import time

from eth_account.account import Account
from fixedpointmath import FixedPoint
from web3.types import RPCEndpoint

from agent0 import IChain, IHyperdrive, PolicyZoo
from agent0.chainsync.db.api import balance_of
from agent0.core import build_account_config_from_env
from agent0.core.base import Quantity, TokenType
from agent0.core.hyperdrive import HyperdriveAgent
from agent0.core.hyperdrive.agent import build_wallet_positions_from_chain, build_wallet_positions_from_db
from agent0.core.hyperdrive.interactive.exec import check_for_new_block
from agent0.core.hyperdrive.interactive.i_hyperdrive_agent import IHyperdriveAgent
from agent0.ethpy import build_eth_config

# Define the unique env filename to use for this script
ACCOUNT_ENV_FILE = "fuzz_test_bots.account.env"
STOP_CHAIN_ON_CRASH = False
# Number of bots
NUM_RANDOM_AGENTS = 2
NUM_RANDOM_HOLD_AGENTS = 2
# The amount of base token each bot receives
# We don't have access to the pool liquidity here,
# but we assume this is enough base to make trades that are at the pool's max
BASE_BUDGET_PER_BOT = FixedPoint("10_000_000")
ETH_BUDGET_PER_BOT = FixedPoint("1_000")
# The slippage tolerance for trades
SLIPPAGE_TOLERANCE = FixedPoint("0.01")  # 1% slippage
# Retry latency & exponential backoff
START_LATENCY = 1
BACKOFF = 2

# Make sure the bots have at least 10% of their budget after each trade
minimum_avg_agent_base = BASE_BUDGET_PER_BOT / FixedPoint(10)

# Get config and addresses
eth_config = build_eth_config(dotenv_file="eth.env")
rng_seed = random.randint(0, 10000000)

# TODO: Do I need to run setup_logging and setup_hyperdrive_crash_report_logging?

# Connect to the chain
chain = IChain(eth_config.rpc_uri)

hyperdrive_addresses = IHyperdrive.Addresses.from_artifacts_uri(eth_config.artifacts_uri)
hyperdrive_config = IHyperdrive.Config(
    preview_before_trade=True,
    rng_seed=rng_seed,
    log_to_rollbar=True,
    rollbar_log_prefix="fuzzbots",
    crash_log_level=logging.CRITICAL,
    crash_report_additional_info={"rng_seed": rng_seed},
)
hyperdrive_pool = IHyperdrive(chain, hyperdrive_addresses, hyperdrive_config)

# Build accounts env var
# This function writes a user defined env file location.
# If it doesn't exist, create it based on agent_config
# (If os.environ["DEVELOP"] is False, will clean exit and print instructions on how to fund agent)
# If it does exist, read it in and use it
account_key_config = build_account_config_from_env(ACCOUNT_ENV_FILE)

# Run agents
# if bots crash, we us an RPC to stop mining anvil
try:
    # Initialize & fund agents
    agents: list[IHyperdriveAgent] = []
    wallet_addrs: list[str] = []
    for _ in range(NUM_RANDOM_AGENTS):
        agent: IHyperdriveAgent = hyperdrive_pool.init_agent(
            private_key=account_key_config.AGENT_KEYS[len(agents)],
            policy_config=PolicyZoo.random.Config(
                slippage_tolerance=SLIPPAGE_TOLERANCE,
                trade_chance=FixedPoint("0.8"),
                randomly_ignore_slippage_tolerance=True,
            ),
        )
        temp_user_account = HyperdriveAgent(Account().from_key(account_key_config.USER_KEY))
        # TODO: Verify that the config should be the scaled_value version)
        agent.add_funds(
            base=FixedPoint(scaled_value=account_key_config.AGENT_BASE_BUDGETS[len(agents)]),
            eth=FixedPoint(scaled_value=account_key_config.AGENT_ETH_BUDGETS[len(agents)]),
            signer_account=temp_user_account,
        )
        agents.append(agent)
        wallet_addrs.append(str(agent.checksum_address))

    for _ in range(NUM_RANDOM_HOLD_AGENTS):
        agent: IHyperdriveAgent = hyperdrive_pool.init_agent(
            private_key=account_key_config.AGENT_KEYS[len(agents)],
            policy_config=PolicyZoo.random_hold.Config(
                slippage_tolerance=SLIPPAGE_TOLERANCE,
                trade_chance=FixedPoint("0.8"),
                randomly_ignore_slippage_tolerance=True,
                max_open_positions=2_000,
            ),
        )
        temp_user_account = HyperdriveAgent(Account().from_key(account_key_config.USER_KEY))
        # TODO: Verify that the config should be the scaled_value version)
        agent.add_funds(
            base=FixedPoint(scaled_value=account_key_config.AGENT_BASE_BUDGETS[len(agents)]),
            eth=FixedPoint(scaled_value=account_key_config.AGENT_ETH_BUDGETS[len(agents)]),
            signer_account=temp_user_account,
        )
        agents.append(agent)
        wallet_addrs.append(str(agent.checksum_address))

    # Load existing wallet balances
    if eth_config.database_api_uri is not None:
        # Get existing open positions from db api server
        balances = balance_of(eth_config.database_api_uri, wallet_addrs)
        # Set balances of wallets based on db and chain
        for agent, address in zip(agents, wallet_addrs):
            # TODO is this the right location for this to happen?
            # On one hand, doing it here makes sense because parameters such as db uri doesn't have to
            # be passed in down all the function calls when wallets are initialized.
            # On the other hand, we initialize empty wallets just to overwrite here.
            # Keeping here for now for later discussion
            agent.wallet = build_wallet_positions_from_db(
                address, balances, hyperdrive_pool.interface.base_token_contract
            )
    else:
        for agent, address in zip(agents, wallet_addrs):
            agent.agent.wallet = build_wallet_positions_from_chain(
                address,
                hyperdrive_pool.interface.hyperdrive_contract,
                hyperdrive_pool.interface.base_token_contract,
            )

    last_executed_block_number = 0
    poll_latency = START_LATENCY + random.uniform(0, 1)
    while True:
        # Check if all agents done trading
        # If so, exit cleanly
        # The done trading state variable gets set internally
        if all(agent.done_trading for agent in agents):
            break
        is_new_block, latest_block = check_for_new_block(hyperdrive_pool.interface, last_executed_block_number)
        if not is_new_block:
            time.sleep(poll_latency)
            poll_latency *= BACKOFF
            poll_latency += random.uniform(0, 1)
        else:
            # Reset backoff
            poll_latency = START_LATENCY + random.uniform(0, 1)
            last_executed_block_number = hyperdrive_pool.interface.get_block_number(latest_block)
            # Execute the agent policies
            # TODO: make this async
            gathered_trade_results = []
            for agent in agents:
                if not agent.done_trading:
                    for result in agent.execute_policy_action():
                        gathered_trade_results.append(result)
            # Update agent funds
            if minimum_avg_agent_base is not None:
                if (
                    sum(agent.wallet.balance.amount for agent in agents) / FixedPoint(len(agents))
                    < minimum_avg_agent_base
                ):
                    # Update agent accounts with new wallet balances
                    for agent in agents:
                        temp_user_account = HyperdriveAgent(Account().from_key(account_key_config.USER_KEY))
                        # TODO: Verify that the config should be the scaled_value version)
                        agent.add_funds(
                            base=FixedPoint(scaled_value=account_key_config.AGENT_BASE_BUDGETS[len(agents)]),
                            eth=FixedPoint(scaled_value=account_key_config.AGENT_ETH_BUDGETS[len(agents)]),
                            signer_account=temp_user_account,
                        )
                        # Contract call to get base balance
                        (_, base_amount) = hyperdrive_pool.interface.get_eth_base_balances(agent.agent)
                        agent.wallet.balance = Quantity(amount=base_amount, unit=TokenType.BASE)

# Don't stop chain if the user interrupts
except KeyboardInterrupt:
    sys.exit()
except Exception as exc:  # pylint: disable=broad-exception-caught
    if STOP_CHAIN_ON_CRASH:
        hyperdrive_pool.interface.web3.provider.make_request(method=RPCEndpoint("evm_setIntervalMining"), params=[0])
    raise exc
