"""Script for fuzzing profit values on immediately opening & closing a long or short."""
# %%
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement

import numpy as np
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import Chain, InteractiveHyperdrive, LocalChain

# TODO: change this into an executable script with LOCAL=False always once we're sure it is working
LOCAL = True

# %%
# Parameters for local chain initialization, defines defaults in constructor
# TODO: boot up Anvil such that it never ticks the block unless we tell it to
if LOCAL:
    chain_config = LocalChain.Config()
    chain = LocalChain(config=chain_config)
else:
    chain_config = Chain.Config(db_port=5004, remove_existing_db_container=True)
    chain = Chain(rpc_uri="http://localhost:8545", config=chain_config)

# %%
# Parameters for pool initialization.
initial_pool_config = InteractiveHyperdrive.Config()
interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)

# %%
# Get a random trade amount
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
close_long_event = hyperdrive_agent0.close_long(
    maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
)
# %%
# TODO:
# Ensure that the prior trades did not result in a profit
open_long_event
close_long_event
hyperdrive_agent0.wallet

# %%
# Open a short and close it immediately
open_short_event = hyperdrive_agent0.open_short(bonds=trade_amount)
close_short_event = hyperdrive_agent0.close_short(
    maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
)
# %%
# TODO:
# Ensure that the prior trades did not result in a profit (should be a loss bc of fee)
open_short_event
close_short_event
hyperdrive_agent0.wallet

# %%
# Add liquidity and redeem it immediately
add_liquidity_event = hyperdrive_agent0.add_liquidity(base=trade_amount)
remove_liquidity_event = hyperdrive_agent0.remove_liquidity(shares=add_liquidity_event.lp_amount)
# %%
# TODO:
# Ensure that the prior trades did not result in a profit (should be a loss bc of fee)
add_liquidity_event
remove_liquidity_event
hyperdrive_agent0.wallet
