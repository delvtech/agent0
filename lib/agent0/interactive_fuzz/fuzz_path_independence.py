"""Script to verify that the state of pool reserves is invariant to the order in which positions are closed."""
# %%
from __future__ import annotations

import numpy as np
import pandas as pd
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import Chain, InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.interactive.event_types import OpenLong, OpenShort
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent
from agent0.hyperdrive.state.hyperdrive_actions import HyperdriveActionType

# %%
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement


# TODO: change this into an executable script with LOCAL=False always once we're sure it is working
LOCAL = True
NUM_TRADES = 3
NUM_PATHS_CHECKED = 10

# %%
# Parameters for local chain initialization, defines defaults in constructor
if LOCAL:
    chain_config = LocalChain.Config()
    chain = LocalChain(config=chain_config)
else:
    chain_config = Chain.Config(db_port=5004, remove_existing_db_container=True)
    chain = Chain(rpc_uri="http://localhost:8545", config=chain_config)
rng = np.random.default_rng()  # No seed, we want this to be random every time it is executed

# %%
# Parameters for pool initialization.
initial_pool_config = InteractiveHyperdrive.Config()
interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)


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
# Get reserve levels
check_columns = [
    "share_reserves",
    "shorts_outstanding",
    "withdrawal_shares_proceeds",
    "share_price",
    "long_exposure",
    # Added in addition to original script
    "bond_reserves",
    "lp_total_supply",
    "longs_outstanding",
]

# TODO add these to pool info
pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
# This is pool config? Shouldn't change
# start_minimum_share_reserves = pool_state.pool_config.minimum_share_reserves
start_hyperdrive_balance = pool_state.hyperdrive_base_balance
start_gov_fees_accrued = pool_state.gov_fees_accrued
start_total_shares = pool_state.vault_shares


# %%
# Open some trades
# TODO: include add liquidity
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
# snapshot the chain, so we can load the snapshot & close in different orders
chain.save_snapshot()

# %%
for iteration in range(NUM_PATHS_CHECKED):
    print(iteration)
    # TODO:
    # Load the snapshot
    chain.load_snapshot()

    # Randomly grab some trades & close them one at a time
    # TODO: Add remove liquidity; withdraw shares would have to happen after & outside this loop
    for trade_index in rng.permuted(list(range(len(trade_events)))):
        agent, trade = trade_events[int(trade_index)]
        if isinstance(trade, OpenLong):
            agent.close_long(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
        if isinstance(trade, OpenShort):
            agent.close_short(maturity_time=trade.maturity_time, bonds=trade.bond_amount)

    # Check the reserve amounts; they should be unchanged now that all of the trades are closed

    pool_info_df = interactive_hyperdrive.get_pool_info(coerce_float=False)

    pd.testing.assert_series_equal(
        pool_info_df[check_columns].iloc[0], pool_info_df[check_columns].iloc[-1], check_names=False
    )

    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
    assert (
        start_hyperdrive_balance == pool_state.hyperdrive_base_balance
    ), f"{start_hyperdrive_balance=} != {pool_state.hyperdrive_base_balance}"
    assert (
        start_gov_fees_accrued == pool_state.gov_fees_accrued
    ), f"{start_gov_fees_accrued=} != {pool_state.gov_fees_accrued}"
    assert start_total_shares == pool_state.vault_shares, f"{start_total_shares=} != {pool_state.vault_shares}"
