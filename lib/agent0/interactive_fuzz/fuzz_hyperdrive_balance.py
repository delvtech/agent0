"""Fuzz test to verify that if all of the funds are removed from Hyperdrive, there is no base left in the contract."""
# %%

from __future__ import annotations

import numpy as np
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.interactive.event_types import OpenLong, OpenShort
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent
from agent0.hyperdrive.state.hyperdrive_actions import HyperdriveActionType

# %%
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement


NUM_TRADES = 3

# %%
# Parameters for local chain initialization, defines defaults in constructor
chain_config = LocalChain.Config()
chain = LocalChain(config=chain_config)
# TODO generate a random seed and store the seed in fuzz test report when it fails
rng = np.random.default_rng()  # No seed, we want this to be random every time it is executed

# %%
# Parameters for pool initialization.
initial_pool_config = InteractiveHyperdrive.Config()
interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)

# %%

# Get initial vault shares
pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
initial_vault_shares = pool_state.vault_shares


# %%
# Generate a list of agents that execute random trades
available_actions = np.array([HyperdriveActionType.OPEN_LONG, HyperdriveActionType.OPEN_SHORT])
min_trade = interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount
trade_list: list[tuple[InteractiveHyperdriveAgent, HyperdriveActionType, FixedPoint]] = []
for agent_index in range(NUM_TRADES):  # 1 agent per trade
    budget = FixedPoint(
        scaled_value=int(np.floor(rng.uniform(low=min_trade.scaled_value * 10, high=int(1e23))))
    )  # Give a little extra money to account for fees
    agent = interactive_hyperdrive.init_agent(base=budget, eth=FixedPoint(100))
    trade_type = rng.choice(available_actions, size=1)[0]
    trade_amount_base = FixedPoint(
        scaled_value=int(
            rng.uniform(
                low=min_trade.scaled_value,
                high=int(
                    budget.scaled_value / 2
                ),  # Don't trade all of their money, to make sure they have enough for fees
            )
        )
    )
    trade_list.append((agent, trade_type, trade_amount_base))


# %%
# Open some trades
trade_events: list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]] = []
for trade in trade_list:
    agent, trade_type, trade_amount = trade
    if trade_type == HyperdriveActionType.OPEN_LONG:
        trade_event = agent.open_long(base=trade_amount)
    elif trade_type == HyperdriveActionType.OPEN_SHORT:
        trade_event = agent.open_short(bonds=trade_amount)
    else:
        raise AssertionError(f"{trade_type=} is not supported.")
    trade_events.append((agent, trade_event))

# %%
# TODO: advance some time

# %%
# Close the trades
for agent, trade in trade_events:
    if isinstance(trade, OpenLong):
        agent.close_long(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
    if isinstance(trade, OpenShort):
        agent.close_short(maturity_time=trade.maturity_time, bonds=trade.bond_amount)

# Check the reserve amounts; they should be unchanged now that all of the trades are closed
pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
assert pool_state.vault_shares == initial_vault_shares, f"{pool_state.vault_shares=} != {initial_vault_shares=}"

# TODO: assert share_reserves >= minimum_share_reserves
