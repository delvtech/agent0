"""Script for fuzzing profit values on immediately opening & closing a long or short."""
# %%
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement

import numpy as np
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain

chain_config = LocalChain.Config()
chain = LocalChain(config=chain_config)

# %%
# Parameters for pool initialization.
initial_pool_config = InteractiveHyperdrive.Config()
interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)

# %%
# Get a random trade amount
# TODO generate a random seed and store the seed in fuzz test report when it fails
rng = np.random.default_rng()  # No seed, we want this to be random every time it is executed
trade_amount = FixedPoint(
    scaled_value=int(
        np.floor(
            rng.uniform(
                low=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount.scaled_value,
                high=int(1e23),
            )
        )
    )
)

# %%
# Generate funded trading agent
hyperdrive_agent0 = interactive_hyperdrive.init_agent(base=trade_amount, eth=FixedPoint(100), name="alice")

# %%
# Open a long and close it immediately
open_long_event = hyperdrive_agent0.open_long(base=trade_amount)
# TODO: Let some amount of time, less than a checkpoint, pass
close_long_event = hyperdrive_agent0.close_long(
    maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
)
# %%
# Ensure that the prior trades did not result in a profit
assert close_long_event.base_amount < open_long_event.base_amount
assert hyperdrive_agent0.wallet.balance.amount < trade_amount

# %%
# Open a short and close it immediately
# Set trade amount to the new wallet position (due to losing money from the previous open/close)
trade_amount = hyperdrive_agent0.wallet.balance.amount
open_short_event = hyperdrive_agent0.open_short(bonds=trade_amount)
# TODO: Let some amount of time pass, less than a checkpoint, pass
close_short_event = hyperdrive_agent0.close_short(
    maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
)
# %%
# Ensure that the prior trades did not result in a profit (should be a loss bc of fee)
assert close_short_event.base_amount < open_short_event.base_amount
assert hyperdrive_agent0.wallet.balance.amount < trade_amount
