"""Runs random bots against the local chain for fuzz testing."""

from __future__ import annotations

import logging
import random
import sys

from fixedpointmath import FixedPoint
from web3.types import RPCEndpoint

from agent0 import IChain, IHyperdrive, PolicyZoo
from agent0.core.base.make_key import make_private_key
from agent0.core.hyperdrive.interactive.i_hyperdrive_agent import IHyperdriveAgent
from agent0.ethpy import build_eth_config

# Crash behavior
STOP_CHAIN_ON_CRASH = False
# Number of bots
NUM_RANDOM_AGENTS = 2
NUM_RANDOM_HOLD_AGENTS = 2
# The amount of base tokens & ETH each bot receives
BASE_BUDGET_PER_BOT = FixedPoint("10_000_000")
ETH_BUDGET_PER_BOT = FixedPoint("1_000")
# The slippage tolerance for trades
SLIPPAGE_TOLERANCE = FixedPoint("0.01")  # 1% slippage

# Make sure the bots have at least 10% of their budget after each trade
minimum_avg_agent_base = BASE_BUDGET_PER_BOT / FixedPoint(10)

# Get config and addresses
eth_config = build_eth_config(dotenv_file="eth.env")
rng_seed = random.randint(0, 10000000)

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

# Run agents
# if bots crash, we us an RPC to stop mining anvil
# Initialize & fund agents
agents: list[IHyperdriveAgent] = []
wallet_addrs: list[str] = []
for _ in range(NUM_RANDOM_AGENTS):
    # Initialize & fund agent using a random private key
    agent: IHyperdriveAgent = hyperdrive_pool.init_agent(
        private_key=make_private_key(),
        policy_config=PolicyZoo.random.Config(
            slippage_tolerance=SLIPPAGE_TOLERANCE,
            trade_chance=FixedPoint("0.8"),
            randomly_ignore_slippage_tolerance=True,
        ),
    )
    agent.set_max_approval()
    agent.add_funds(base=BASE_BUDGET_PER_BOT, eth=ETH_BUDGET_PER_BOT)
    agents.append(agent)

for _ in range(NUM_RANDOM_HOLD_AGENTS):
    agent: IHyperdriveAgent = hyperdrive_pool.init_agent(
        private_key=make_private_key(),
        policy_config=PolicyZoo.random_hold.Config(
            slippage_tolerance=SLIPPAGE_TOLERANCE,
            trade_chance=FixedPoint("0.8"),
            randomly_ignore_slippage_tolerance=True,
            max_open_positions=2_000,
        ),
    )
    agent.set_max_approval()
    agent.add_funds(base=BASE_BUDGET_PER_BOT, eth=ETH_BUDGET_PER_BOT)
    agents.append(agent)

# Make trades until the user or agents stop us
while True:
    # Execute the agent policies
    for agent in agents:
        try:
            _ = agent.execute_policy_action()
            # Update agent funds
            if minimum_avg_agent_base is not None:
                if (
                    sum(agent.wallet.balance.amount for agent in agents) / FixedPoint(len(agents))
                    < minimum_avg_agent_base
                ):
                    for agent in agents:
                        agent.add_funds(base=BASE_BUDGET_PER_BOT, eth=ETH_BUDGET_PER_BOT)

        # Don't stop chain if the user interrupts
        except KeyboardInterrupt:
            sys.exit()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            if STOP_CHAIN_ON_CRASH:
                hyperdrive_pool.interface.web3.provider.make_request(
                    method=RPCEndpoint("evm_setIntervalMining"), params=[0]
                )
            raise exc
