"""Script to verify that the state of pool reserves is invariant to the order in which positions are closed."""
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


NUM_TRADES = 10

# %%
# Parameters for local chain initialization, defines defaults in constructor
# set a large block time so i can manually control when it ticks
# TODO: set block time really high after contracts deployed:
# chain_config = LocalChain.Config(block_time=1_000_000)
chain_config = LocalChain.Config()
chain = LocalChain(config=chain_config)
random_seed = np.random.randint(low=1, high=99999999)  # No seed, we want this to be random every time it is executed
rng = np.random.default_rng(random_seed)

# %%
# Parameters for pool initialization.
initial_pool_config = InteractiveHyperdrive.Config()
interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)
signer = interactive_hyperdrive.init_agent(eth=FixedPoint(100))

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

# automatically created by sending transactions
starting_checkpoint = interactive_hyperdrive.hyperdrive_interface.current_pool_state.checkpoint

# %%
# advance the time to at least the position duration, maximum of two position durations.

position_duration = interactive_hyperdrive.hyperdrive_interface.pool_config.position_duration
rng = np.random.default_rng()  # No seed, we want this to be random every time it is executed
extra_time = int(np.floor(rng.uniform(low=0, high=position_duration)))

# advances time and mines a block
current_time = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
checkpoint_duration = interactive_hyperdrive.hyperdrive_interface.pool_config.checkpoint_duration

starting_checkpoint_time = current_time - current_time % checkpoint_duration

chain.advance_time(position_duration + 30)

# create a checkpoint
current_time = interactive_hyperdrive.hyperdrive_interface.current_pool_state.block_time
interactive_hyperdrive.hyperdrive_interface.create_checkpoint(signer.agent)
chain.advance_time(extra_time)

maturity_checkpoint_time = current_time - current_time % checkpoint_duration
maturity_checkpoint = interactive_hyperdrive.hyperdrive_interface.hyperdrive_contract.functions.getCheckpoint(
    maturity_checkpoint_time
).call()
# %%
# close them one at a time, check invariants

SECONDS_PER_YEAR = 60 * 60 * 24 * 365


def assertion(condition: bool, message: str = "Assertion failed."):
    """Simple assertion check.

    Parameters
    ----------
    condition : bool
        condition to check.
    message : str, optional
        Error message if condtion fails.
    """
    if not condition:
        print(message)


for index, (agent, trade) in enumerate(trade_events):
    print(f"{index=}\n")
    if isinstance(trade, OpenLong):
        close_long_event = agent.close_long(maturity_time=trade.maturity_time, bonds=trade.bond_amount)
        # 0.05 would be a 5% fee.
        flat_fee_percent = interactive_hyperdrive.hyperdrive_interface.pool_config.fees.flat
        # base out should be equal to bonds in minus the flat fee.

        # assert with trade values
        actual_base_amount = close_long_event.base_amount
        expected_base_amount_from_event = close_long_event.bond_amount - close_long_event.bond_amount * flat_fee_percent
        # assertion(actual_base_amount == expected_base_amount_from_event)

        # assert with event values
        expected_base_amount_from_trade = trade.bond_amount - trade.bond_amount * flat_fee_percent
        # assertion(close_long_event.base_amount == expected_base_amount_from_trade)

        # show the difference
        difference = actual_base_amount.scaled_value - expected_base_amount_from_trade.scaled_value
        print(f"close long: {actual_base_amount.to_decimal()}")
        print(f"close long: difference in wei {difference}\n")
        # assert actual_base_amount == expected_base_amount
        # assert close_long_event.base_amount == trade.bond_amount - trade.bond_amount * flat_fee_percent
    if isinstance(trade, OpenShort):
        close_short_event = agent.close_short(maturity_time=trade.maturity_time, bonds=trade.bond_amount)

        # get the share prices
        open_share_price = starting_checkpoint.share_price
        closing_share_price = FixedPoint(scaled_value=maturity_checkpoint.sharePrice)

        # interested accrued in shares = (c1 / c0 + flat_fee) * dy - c1 * dz
        flat_fee_percent = interactive_hyperdrive.hyperdrive_interface.pool_config.fees.flat

        # get the share amount, c1 * dz part of the equation.
        share_reserves_delta = trade.bond_amount
        flat_fee = trade.bond_amount * flat_fee_percent
        share_reserves_delta_plus_flat_fee = share_reserves_delta + flat_fee

        interest_accrued = (
            trade.bond_amount * (closing_share_price / open_share_price + flat_fee_percent)
            - share_reserves_delta_plus_flat_fee
        )

        # assert and show the difference
        # assertion(close_short_event.base_amount == interest_accrued)
        difference = close_short_event.base_amount.scaled_value - interest_accrued.scaled_value
        print(f"close short: {close_short_event.base_amount}")
        print(f"close short: difference in wei {difference}\n")
        # assert close_short_event.base_amount == interest_accrued
