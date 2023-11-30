"""Example script for using interactive hyperdrive."""
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
trade_amount = rng.uniform(
    low=interactive_hyperdrive.hyperdrive_interface.pool_config.minimum_transaction_amount, high=int(1e23)
)

# %%
# Generate funded trading agents from the interactive object
hyperdrive_agent0 = interactive_hyperdrive.init_agent(
    base=FixedPoint(scaled_value=trade_amount * 2), eth=FixedPoint(100), name="alice"
)

# %%
# Open a long and close it immediately
open_long_event_1 = hyperdrive_agent0.open_long(base=FixedPoint(scaled_value=trade_amount))
close_long_event_1 = hyperdrive_agent0.close_long(
    maturity_time=open_long_event_1.maturity_time, bonds=open_long_event_1.bond_amount
)
# %%
# TODO:
# Ensure that the prior trades did not result in a profit
open_long_event_1
close_long_event_1
hyperdrive_agent0.wallet
