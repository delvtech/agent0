"""Script for fuzzing profit values on immediately opening & closing a long or short."""
# %%
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement

from typing import cast

import numpy as np
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import Chain, InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.interactive.event_types import OpenLong, OpenShort
from agent0.hyperdrive.interactive.interactive_hyperdrive_agent import InteractiveHyperdriveAgent
from agent0.hyperdrive.state.hyperdrive_actions import HyperdriveActionType

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

available_actions = [HyperdriveActionType.OPEN_LONG, HyperdriveActionType.OPEN_SHORT]
min_trade = interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount
trade_list: list[tuple[InteractiveHyperdriveAgent, HyperdriveActionType, FixedPoint]] = []
for agent_index in range(NUM_TRADES):  # 1 agent per trade
    budget = FixedPoint(
        scaled_value=rng.uniform(low=min_trade * 10, high=int(1e23))
    )  # Give a little extra money to account for fees
    agent = interactive_hyperdrive.init_agent(base=FixedPoint(scaled_value=budget), eth=FixedPoint(100))
    trade_type = cast(HyperdriveActionType, rng.choice(available_actions, size=1))
    trade_amount_base = FixedPoint(
        rng.uniform(
            low=min_trade.scaled_value,
            high=int(budget.scaled_value / 2),  # Don't trade all of their money, to make sure they have enough for fees
        )
    )
    trade_list.append((agent, trade_type, trade_amount_base))

# %%
# Get reserve levels
pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
start_share_reserves = pool_state.pool_info.share_reserves
start_shorts_outstanding = pool_state.pool_info.shorts_outstanding
start_withdraw_pool_proceeds = pool_state.pool_info.withdrawal_shares_proceeds
start_minimum_share_reserves = pool_state.pool_config.minimum_share_reserves
start_share_price = pool_state.pool_info.share_price
start_global_exposure = pool_state.pool_info.long_exposure
start_hyperdrive_balance = pool_state.hyperdrive_balance
start_gov_fees_accrued = pool_state.gov_fees_accrued
start_total_shares = pool_state.vault_shares


# %%
# Open some trades
trade_events: list[tuple[InteractiveHyperdriveAgent, OpenLong | OpenShort]] = []
for trade in trade_list:
    agent, trade_type, trade_amount = trade
    if trade_type == HyperdriveActionType.OPEN_LONG:
        trade_event = agent.open_long(trade_amount.scaled_value)
    elif trade_type == HyperdriveActionType.OPEN_SHORT:
        trade_event = agent.close_long(trade_amount.scaled_value)
    else:
        raise AssertionError(f"{trade['trade_type']=} is not supported.")
    trade_events.append(trade_event)

# %%
# TODO:
# snapshot the chain, so we can load the snapshot & close in different orders

# %%
for _ in range(NUM_PATHS_CHECKED):
    # TODO:
    # load the snapshot

    # randomly grab some trades & close them one at a time
    for trade_index in rng.permuted(list(range(len(trade_events)))):
        agent, trade = trade_events[trade_index]
        if isinstance(trade, OpenLong):
            agent.close_long(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
        if isinstance(trade, OpenShort):
            agent.close_short(maturity_time=trade.maturity_time, bonds=trade.bond_amount)

    # Check the reserve amounts; they should be unchanged now that all of the trades are closed
    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
    assert (
        start_share_reserves == pool_state.pool_info.share_reserves
    ), f"{start_share_reserves=} != {pool_state.pool_info.share_reserves}"
    assert (
        start_shorts_outstanding == pool_state.pool_info.shorts_outstanding
    ), f"{start_shorts_outstanding=} != {pool_state.pool_info.shorts_outstanding}"
    assert (
        start_withdraw_pool_proceeds == pool_state.pool_info.withdrawal_shares_proceeds
    ), f"{start_withdraw_pool_proceeds=} != {pool_state.pool_info.withdrawal_shares_proceeds}"
    assert (
        start_share_price == pool_state.pool_info.share_price
    ), f"{start_share_price=} != {pool_state.pool_info.share_price}"
    assert (
        start_global_exposure == pool_state.pool_info.long_exposure
    ), f"{start_global_exposure=} != {pool_state.pool_info.long_exposure}"
    assert (
        start_hyperdrive_balance == pool_state.hyperdrive_balance
    ), f"{start_hyperdrive_balance=} != {pool_state.hyperdrive_balance}"
    assert (
        start_gov_fees_accrued == pool_state.gov_fees_accrued
    ), f"{start_gov_fees_accrued=} != {pool_state.gov_fees_accrued}"
    assert start_total_shares == pool_state.vault_shares, f"{start_total_shares=} != {pool_state.vault_shares}"
