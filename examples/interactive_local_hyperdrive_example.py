"""Example script for using interactive hyperdrive to launch a local chain."""

# %%
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement

import datetime

from fixedpointmath import FixedPoint

from agent0 import LocalChain, LocalHyperdrive, PolicyZoo

# %% [markdown]
#####################
# Initialization
#####################

# %%
# Parameters for local chain initialization, defines defaults in constructor
local_chain_config = LocalChain.Config()

# Launches a local chain in a subprocess
# This also launches a local postgres docker container for data under the hood, attached to the chain.
chain = LocalChain(local_chain_config)

# Initialize agents from the chain
# %%
# Generate funded trading agents from the interactive object
# Names are reflected on output data frames and plots later
# NOTE a local chain can initialize with base and eth.
# Base is a mock token used for all underlying pools deployed.
agent0 = chain.init_agent(base=FixedPoint(100_000_000), eth=FixedPoint(100), name="agent0")
agent1 = chain.init_agent(base=FixedPoint(100_000), eth=FixedPoint(100), name="agent1")
# Omission of name defaults to wallet address
agent2 = chain.init_agent(base=FixedPoint(100_000), eth=FixedPoint(10))
# Add funds to an agent
agent0.add_funds(base=FixedPoint(100000), eth=FixedPoint(100))

# %%
# Initialize the interactive object with specified initial pool parameters and the chain to launch hyperdrive on.
# An "admin" user (as provided by the Chain object) is launched/funded here for deploying hyperdrive.
# Alternatively, you can pass in one of the agents to use as the deployer. If you do this, ensure
# there is enough base to cover the initial funding (defaults to 100_000 base.), and enough eth to cover gas.

# Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
# Launches 2 pools on the same local chain

# Hyperdrive0 uses the anvil admin account to deploy. The config object is automatically build.
hyperdrive0 = LocalHyperdrive(chain)
# Hyperdrive1 uses agent0 as the deployer
initial_pool_config = LocalHyperdrive.Config(initial_liquidity=FixedPoint(100_000))
hyperdrive1 = LocalHyperdrive(chain, initial_pool_config, deployer=agent0)

# %% [markdown]
#####################
# Executing Trades
#####################

# %%
# Here, we execute a trade on a pool.
# Return values here mirror the various events emitted from these contract calls
# Here, base is unitless and is dependent on the underlying tokens the pool uses.
open_long_event_1 = agent0.open_long(base=FixedPoint(11111), pool=hyperdrive0)

# %%
# We can also set an active pool an agent is using to avoid passing in the pool
# for every trade.
agent1.set_active_pool(hyperdrive0)
open_long_event_2 = agent1.open_long(base=FixedPoint(22222))

# Close previous longs from events
close_long_event_1 = agent0.close_long(
    maturity_time=open_long_event_1.maturity_time,
    bonds=open_long_event_1.bond_amount,
    pool=hyperdrive0,
)

# Close previous longs from the wallet
# This wallet is a wallet object that contains positions relevant to a specific pool.
# This takes a snapshot of the current wallet positions.
agent0.get_positions(pool=hyperdrive0)
# agent1's active pool is set, so no need to pass in a pool.
agent1.get_positions()
# We also provide helper functions to get specific position types.
agent1_longs = agent1.get_longs()
close_long_event_2 = agent1.close_long(maturity_time=agent1_longs[0].maturity_time, bonds=agent1_longs[0].balance)

# Shorts
open_short_event = agent1.open_short(bonds=FixedPoint(33333))
agent1_shorts = agent1.get_shorts()
close_short_event = agent1.close_short(maturity_time=agent1_shorts[0].maturity_time, bonds=agent1_shorts[0].bond_amount)

# LP
add_lp_event = agent1.add_liquidity(base=FixedPoint(44444))
remove_lp_event = agent1.remove_liquidity(shares=agent1.get_lp())

# The above trades doesn't result in withdraw shares, but the function below allows you
# to withdrawal shares from the pool.
# withdraw_shares_event = agent1.redeem_withdraw_share(shares=agent1.get_withdraw_shares())

# %%

# Agents can also execute policies, which encapsulates actions to take on a pool.
# This requires initializing a policy class. For example, we initialize a policy that makes random trades.
random_policy_config = PolicyZoo.random.Config(rng_seed=123)
random_policy = PolicyZoo.random(random_policy_config)

# Execute policy trade on a pool
# Output event is one of the possible trade events
agent0_trades = []
for i in range(10):
    # NOTE Since a policy can execute multiple trades per action, the output events is a list
    agent0.execute_policy_action(policy=random_policy, pool=hyperdrive0)

# Similar to pools, we can set an active policy for an agent
agent1.set_active_policy(random_policy)
agent1_trades = []
for i in range(10):
    agent1.execute_policy_action()

# %% [markdown]
#####################
# Simulation Management
#####################

# %%
# The local chain and hyperdrive objects provide various simulation tools, such as
# advancing time, snapshotting, and controlling the underlying variable yield rate.

# Advancing time.
# NOTE these calls are chainwide calls, so all pools connected to this chain gets affected.
# Advance time, accepts timedelta or seconds
# The option `create_checkpoints` creates hyperdrive checkpoints when advancing time
# but this call may be slow when advancing a large amount of time.
chain.advance_time(datetime.timedelta(weeks=52), create_checkpoints=False)
chain.advance_time(3600, create_checkpoints=True)

# Snapshotting.
# Only one snapshot can be saved at a time. New snapshots made overwrite previous snapshots.
chain.save_snapshot()
chain.load_snapshot()

# Set the underlying yield variable rate
hyperdrive0.set_variable_rate(FixedPoint("0.10"))

# %% [markdown]
#####################
# Analysis
#####################

# %%
# Runs a dashboard showing various metrics on the pool.
# This function automatically opens a browser tab with a dashboard.
# Blocking mode waits for a keyboard press, then kills the dashboard server.
# Non-blocking mode keeps the server running until cleanup.
hyperdrive0.run_dashboard(blocking=True)

# %%
# These functions queries the underlying database to get data. All functions here return
# a pandas dataframe.

# Get data from database wrt a hyperdrive pool.
pool_config = hyperdrive0.get_pool_config()
# The underlying data is in Decimal format, which is lossless. We don't care about precision
# here, and pandas need a numerical float for plotting, so we coerce decimals to floats here
# TODO this pool state contains pool_info + pool_analysis, which is different from the
# interface and sdk's pool state, which contains pool config + pool_info.
# We may want to change this function's name to avoid confusion.
pool_state = hyperdrive0.get_pool_state(coerce_float=True)
checkpoint_info = hyperdrive0.get_checkpoint_info()
ticker = hyperdrive0.get_ticker()

pool_positions = hyperdrive0.get_current_positions()
positions_over_time = hyperdrive0.get_positions_over_time()
pnl_over_time = hyperdrive0.get_pnl_over_time(coerce_float=True)

# Get data from the database wrt an agent
# This function shows an agent's wallet across all pools.
agent0_wallet = agent0.get_wallet()

# Since this data is pandas, we can utilize pandas plotting functions
pool_state.plot(x="block_number", y="longs_outstanding", kind="line")
# Change wallet_address to be columns for plotting
pnl_over_time.pivot(index="block_number", columns="username", values="pnl").plot()

# %% [markdown]
#####################
# Cleanup
#####################
# %%
# Cleanup resources
chain.cleanup()
