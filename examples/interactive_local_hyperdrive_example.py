"""An example of using agent0 to simulate hyperdrive on a local chain."""

# %%
import datetime

from fixedpointmath import FixedPoint

from agent0 import LocalChain, LocalHyperdrive, PolicyZoo

# %% [markdown]
#####################
# Initialization
#####################

# %%
# Parameters for local chain initialization, defines defaults in constructor.
local_chain_config = LocalChain.Config()

# Launches a local chain in a subprocess.
# This also launches a local postgres docker container for data under the hood, attached to the chain.
chain = LocalChain(local_chain_config)

# Initialize agents from the chain
# %%
# Generate funded trading agents from the interactive object.
# Names are reflected on output data frames and plots later.
# We initialize these agents with eth.
agent0 = chain.init_agent(
    eth=FixedPoint(100),
    name="agent0",
)
# We can initialize an agent with an active policy - more on that later
agent1 = chain.init_agent(
    eth=FixedPoint(100),
    name="agent1",
    policy=PolicyZoo.random,
    policy_config=PolicyZoo.random.Config(),
)

# %%
# Deploy two pools with specified parameters on the same chain.
# An "admin" user (as provided by the Chain object) is launched/funded here for deploying hyperdrive.
# Allows setting custom parameters for pool initialization. Optionally omit for default values.
hyperdrive0 = LocalHyperdrive(chain)
initial_pool_config = LocalHyperdrive.Config(initial_liquidity=FixedPoint(100_000))
hyperdrive1 = LocalHyperdrive(chain, initial_pool_config)

# %%

# We explicitly add an active pool to this agent.
# This allows us to mint base in initialization.
# Here, base is unitless and is dependent on the underlying tokens the pool uses.
agent2 = chain.init_agent(base=FixedPoint(100_000), eth=FixedPoint(10), pool=hyperdrive0)

# Add funds to an agent for various pools
agent0.add_funds(base=FixedPoint(1_000_000), pool=hyperdrive0)
agent1.add_funds(base=FixedPoint(100_000), pool=hyperdrive0)


# %% [markdown]
#####################
# Executing Trades
#####################

# %%
# Here, we execute a trade on a pool.
# The return values for trade functions mirror the various events emitted from these contract calls
# Here, base is unitless and is dependent on the underlying tokens the pool uses.
open_long_event_1 = agent0.open_long(base=FixedPoint(11111), pool=hyperdrive0)

# %%
# We can also set an active pool an agent is using to avoid passing in the pool
# for every trade.
agent1.set_active(pool=hyperdrive0)
open_long_event_2 = agent1.open_long(base=FixedPoint(22222))

# Close previous longs from events
close_long_event_1 = agent0.close_long(
    maturity_time=open_long_event_1.args.maturity_time,
    bonds=open_long_event_1.args.bond_amount,
    pool=hyperdrive0,
)

# %%
# We can query the agent for the current wallet.
# This wallet object contains positions relevant to a specific pool.
print(agent0.get_wallet(pool=hyperdrive0))
# %%
# agent1's active pool is set, so no need to pass in a pool.
print(agent1.get_wallet())

# %%
# Close previous longs from the wallet.
# We also provide helper functions to get specific position types.
agent1_longs = agent1.get_longs()
close_long_event_2 = agent1.close_long(maturity_time=agent1_longs[0].maturity_time, bonds=agent1_longs[0].balance)

# Shorts
open_short_event = agent1.open_short(bonds=FixedPoint(33333))
agent1_shorts = agent1.get_shorts()
close_short_event = agent1.close_short(maturity_time=agent1_shorts[0].maturity_time, bonds=agent1_shorts[0].balance)

# LP
add_lp_event = agent1.add_liquidity(base=FixedPoint(44444))
remove_lp_event = agent1.remove_liquidity(shares=agent1.get_lp())

# The `remove_liquidity` trade above doesn't result in delayed lp (i.e., withdrawal shares),
# but the function below allows you to redeem these shares from the pool.
# withdraw_shares_event = agent1.redeem_withdrawal_share(shares=agent1.get_withdrawal_shares())

# %%

# Agents can also execute policies, which encapsulates actions to take on a pool.
# This requires initializing a policy class from the agent.
# For example, we set a policy that makes random trades.
# We can either initialize a policy on initialization (see agent1's initialization),
# or we can explicitly call `set_policy` to set a policy on an agent.
# NOTE: `set_policy` overwrites the existing policy.
agent0.set_active(
    policy=PolicyZoo.random,
    policy_config=PolicyZoo.random.Config(rng_seed=123),
)

# Execute policy trade on a pool
# Output event is one of the possible trade events
agent0_trades = []
for i in range(10):
    # NOTE Since a policy can execute multiple trades per action, the output events is a list.
    agent0_trades.extend(agent0.execute_policy_action(pool=hyperdrive0))

# Agent1's policy was set during initialization
agent1_trades = []
for i in range(10):
    agent1_trades.extend(agent1.execute_policy_action())

# %% [markdown]
#####################
# Simulation Management
#####################

# %%
# The local chain and hyperdrive objects provide various simulation tools, such as
# advancing time, snapshotting, and controlling the underlying variable yield rate.

# Advancing time:
# The `advance_time` function accepts timedelta or seconds.
# The option `create_checkpoints` creates intermediate hyperdrive checkpoints when advancing time
# but this call may be slow when advancing a large amount of time.
# NOTE these calls are chainwide calls, so all pools connected to this chain gets affected.
chain.advance_time(datetime.timedelta(weeks=52), create_checkpoints=False)
chain.advance_time(3600, create_checkpoints=True)

# Snapshotting:
# The chain is able to save a snapshot of the current state, then load to this state later.
# Only one snapshot can be saved at a time. New snapshots made overwrite previous snapshots.
chain.save_snapshot()
chain.load_snapshot()

# Variable rate:
# Set the underlying yield variable rate.
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
chain.run_dashboard(blocking=False)

# %%
# These functions query the underlying database to get data.
# All functions here return a Pandas dataframe.

# Agent level analysis:

# Get the raw trade events across all pools.
agent_trade_events = agent0.get_trade_events()
# Alternatively, get events from a single pool.
agent_trade_events = agent0.get_trade_events(pool_filter=hyperdrive0)
agent_trade_events = agent0.get_trade_events(pool_filter=hyperdrive1)

# Gets all open positions and their corresponding PNL for an agent across all pools.
agent_positions = agent0.get_positions()
# Gets all open and closed positions and their corresponding PNL for an agent across all pools.
agent_positions = agent0.get_positions(show_closed_positions=True)

# %%
# Pool level analysis:

# Get data from database wrt a hyperdrive pool.
pool_config = hyperdrive0.get_pool_config()
# The underlying data is in Decimal format, which is lossless.
# Pandas need a numerical float for plotting, so we coerce decimals to floats.
pool_info = hyperdrive0.get_pool_info(coerce_float=True)
checkpoint_info = hyperdrive0.get_checkpoint_info()

# Query the events and open/closed positions for the pool across all agents
agent_trade_events = hyperdrive0.get_trade_events()
pool_positions = hyperdrive0.get_positions(show_closed_positions=True)
# Gets all positions and their corresponding PNL over time
positions_over_time = hyperdrive0.get_historical_positions()
# Aggregates agents across a pool to get pnl on the pool over time
# We coerce underlying Decimals to floats for plotting
pnl_over_time = hyperdrive0.get_historical_pnl(coerce_float=True)

# %%
# Since this data is pandas, we can utilize pandas plotting functions
pool_info.plot(x="block_number", y="longs_outstanding", kind="line")
# Change wallet_address to be columns for plotting
pnl_over_time.pivot(index="block_number", columns="username", values="pnl").plot()

# %% [markdown]
#####################
# Cleanup
#####################
# %%
# Cleanup resources
chain.cleanup()
