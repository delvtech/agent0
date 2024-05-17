"""Example script for using interactive hyperdrive to launch a local chain."""

# %%
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement

import datetime

from fixedpointmath import FixedPoint

from agent0 import LocalChain, LocalHyperdrive

# %%
# Parameters for local chain initialization, defines defaults in constructor
local_chain_config = LocalChain.Config()
# Launches a local chain in a subprocess
# This also launches a local postgres docker container for data under the hood, attached to the chain.
# Each hyperdrive pool will have it's own database within this container
# NOTE: LocalChain is a subclass of Chain
chain = LocalChain(local_chain_config)
# Can connect to a specific existing chain
# existing_chain = Chain("http://localhost:8545")

# %%
# Initialize the interactive object with specified initial pool parameters and the chain to launch hyperdrive on
# An "admin" user (as provided by the Chain object) is launched/funded here for deploying hyperdrive

# Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
initial_pool_config = LocalHyperdrive.Config()
# Launches 2 pools on the same local chain
hyperdrive = LocalHyperdrive(chain, initial_pool_config)
hyperdrive_2 = LocalHyperdrive(chain, initial_pool_config)

# %%
# Generate funded trading agents from the interactive object
# Names are reflected on output data frames and plots later
agent0 = hyperdrive.init_agent(base=FixedPoint(100000), eth=FixedPoint(100), name="alice")
hyperdrive_agent1 = hyperdrive_2.init_agent(base=FixedPoint(100000), eth=FixedPoint(100), name="bob")
# Omission of name defaults to wallet address
hyperdrive_agent2 = hyperdrive.init_agent(base=FixedPoint(100000), eth=FixedPoint(10))

# Add funds to an agent
agent0.add_funds(base=FixedPoint(100000), eth=FixedPoint(100))

# %%
# Here, we execute a trade, where it's calling agent0 + gather data from data pipeline
# under the hood to allow for error handling and data management
# Return values here mirror the various events emitted from these contract calls
open_long_event_1 = agent0.open_long(base=FixedPoint(11111))
open_long_event_1  # pyright: ignore
# %%

# Another long with a different maturity time
open_long_event_2 = agent0.open_long(FixedPoint(22222))

# View current wallet
print(agent0.get_wallet())


# NOTE these calls are chainwide calls, so all pools connected to this chain gets affected.
# Advance time, accepts timedelta or seconds
# The option `create_checkpoints` creates hyperdrive checkpoints when advancing time
# but this call may be slow when advancing a large amount of time.
chain.advance_time(datetime.timedelta(weeks=52), create_checkpoints=False)
chain.advance_time(3600, create_checkpoints=True)

# Close previous longs
close_long_event_1 = agent0.close_long(
    maturity_time=open_long_event_1.maturity_time, bonds=open_long_event_1.bond_amount
)

agent0_longs = list(agent0.get_wallet().longs.values())
close_long_event_2 = agent0.close_long(maturity_time=agent0_longs[0].maturity_time, bonds=agent0_longs[0].balance)

# Shorts
open_short_event = hyperdrive_agent1.open_short(bonds=FixedPoint(33333))
close_short_event = hyperdrive_agent1.close_short(
    maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
)

# LP
add_lp_event = hyperdrive_agent2.add_liquidity(base=FixedPoint(44444))
remove_lp_event = hyperdrive_agent2.remove_liquidity(shares=hyperdrive_agent2.get_wallet().lp_tokens)

# The above trades doesn't result in withdraw shares, but the function below allows you
# to withdrawal shares from the pool.
# withdraw_shares_event = hyperdrive_agent2.redeem_withdraw_share(shares=hyperdrive_agent2.wallet.withdraw_shares)

# %%
# Get data from database under the hood
pool_config = hyperdrive.get_pool_config()
# The underlying data is in Decimal format, which is lossless. We don't care about precision
# here, and pandas need a numerical float for plotting, so we coerce decimals to floats here
pool_info = hyperdrive.get_pool_info(coerce_float=True)

# FIXME sort these values by checkpoint time
checkpoint_info = hyperdrive.get_checkpoint_info()

# Change this to get wallet
wallet = agent0.get_wallet()

agent_positions = agent0.get_positions()
agent_trade_events = agent0.get_trade_events()

pool_positions = hyperdrive.get_positions()
trade_events = hyperdrive.get_trade_events()
pool_positions_over_time = hyperdrive.get_historical_positions()
total_wallet_pnl_over_time = hyperdrive.get_historical_pnl(coerce_float=True)

# %%
# Plot pretty plots
# TODO these should be in a notebook for plotting
pool_info.plot(x="block_number", y="longs_outstanding", kind="line")
# Change wallet_address to be columns for plotting
total_wallet_pnl_over_time.pivot(index="block_number", columns="username", values="pnl").plot()

# %%
# Cleanup resources
chain.cleanup()
