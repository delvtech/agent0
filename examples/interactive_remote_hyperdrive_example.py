"""An example of using agent0 to execute or analyze trades on a remote chain."""

# %%
# pylint: disable=invalid-name

from fixedpointmath import FixedPoint

from agent0 import Chain, Hyperdrive, LocalChain, LocalHyperdrive, PolicyZoo
from agent0.core.base.make_key import make_private_key

# %% [markdown]
#####################
# Initialization
#####################

# %%
# Set the rpc_uri to the chain, e.g., to sepolia testnet
# rpc_uri = "http://uri.to.sepolia.testnet"

# For this example, we launch a chain and local hyperdrive, and set the rpc_uri and hyperdrive address from these.
local_chain = LocalChain()
local_hyperdrive = LocalHyperdrive(local_chain)
rpc_uri = local_chain.rpc_uri
hyperdrive_address = local_hyperdrive.hyperdrive_address

# Need to set different db port here to avoid port collisions with local chain
chain = Chain(rpc_uri, config=Chain.Config(db_port=1234))

# %%

# Initialize agents

# We set the private key here. In practice, this would be in a private
# env file somewhere, and we only access this through environment variables.
# For now, we generate a random key and explicitly fund it
private_key_0 = make_private_key()
private_key_1 = make_private_key()

# Init from private key
agent0 = chain.init_agent(
    private_key=private_key_0,
    name="agent0",
)
# We can initialize an agent with a custom policy - more on that later
agent1 = chain.init_agent(
    private_key=private_key_1,
    name="agent1",
    policy=PolicyZoo.random,
    policy_config=PolicyZoo.random.Config(),
)

# %%
# Connect to a hyperdrive pool

# Define a specific pool address
# hyperdrive_address = "0x0000000000000000000000000000000000000000"

# Alternatively, look up the list of registered hyperdrive pools
# This is the registry address deployed on sepolia.
# registry_address = "0xba5156E697d39a03EDA824C19f375383F6b759EA"
#
# hyperdrive_address = Hyperdrive.get_hyperdrive_addresses_from_registry(chain, registry_address)["sdai_14_day"]

# We'll use the previously deployed pool for this exapmle

hyperdrive_config = Hyperdrive.Config()
hyperdrive_pool = Hyperdrive(chain, hyperdrive_address, hyperdrive_config)

# %%
# We expose this function for testing purposes, but the underlying function
# calls `mint` and `anvil_set_balance`, which are likely to fail on any non-test
# network. In practice, it's up to the user to ensure the wallet has sufficient funds.
agent0.add_funds(base=FixedPoint(100000), eth=FixedPoint(100), pool=hyperdrive_pool)
agent1.add_funds(base=FixedPoint(100000), eth=FixedPoint(100), pool=hyperdrive_pool)


# %% [markdown]
#####################
# Executing Trades
#####################

# We set agent1's active pool to avoid passing in pool for functions.
agent1.set_active(pool=hyperdrive_pool)

# Set max approval for the agent on a specific pool.
# TODO this is overly permissive, we may want to expose setting approval for a specific
# amount, or allow a parameter in trade calls to approve for the preview amount
# (plus slippage) before executing a trade.
agent0.set_max_approval(pool=hyperdrive_pool)
agent1.set_max_approval()

# %%
# Make trades

# Return values here mirror the various events emitted from these contract calls
# TODO These functions are blocking, expose async versions of the trades below
open_long_event = agent0.open_long(base=FixedPoint(11111), pool=hyperdrive_pool)
close_long_event = agent0.close_long(
    maturity_time=open_long_event.maturity_time,
    bonds=open_long_event.bond_amount,
    pool=hyperdrive_pool,
)

open_short_event = agent1.open_short(bonds=FixedPoint(33333))
agent1_shorts = agent1.get_shorts()
close_short_event = agent1.close_short(maturity_time=agent1_shorts[0].maturity_time, bonds=agent1_shorts[0].balance)

# LP
add_lp_event = agent1.add_liquidity(base=FixedPoint(44444))
remove_lp_event = agent1.remove_liquidity(shares=agent1.get_lp())

# The above trades doesn't result in withdraw shares, but the function below allows you
# to withdrawal shares from the pool.
# withdraw_shares_event = agent1.redeem_withdraw_share(shares=agent1.get_withdraw_shares())


# %%

# Agents can also execute policies, which encapsulates actions to take on a pool.
# This requires initializing a policy class. For example, we initialize a policy that makes random trades.
# We can either initialize a policy on initialization (see agent1's initialization)
# or we can explicitly call `set_policy` to set a policy on an agent.
# NOTE: `set_policy` overwrites the existing policy.
# TODO we may be able to set multiple policies on an agent and hot-swap them

agent0.set_active(
    policy=PolicyZoo.random,
    policy_config=PolicyZoo.random.Config(rng_seed=123),
)

# Execute policy trade on a pool
# Output event is one of the possible trade events
agent0_trades = []
for i in range(10):
    # NOTE Since a policy can execute multiple trades per action, the output events is a list
    agent0_trades.extend(agent0.execute_policy_action(pool=hyperdrive_pool))

# Agent1's policy was set during initialization
agent1_trades = []
for i in range(10):
    agent1_trades.extend(agent1.execute_policy_action())

# %% [markdown]
#####################
# Analysis
#####################

# %%

# Get data from the database wrt an agent
# This function shows an agent's wallet across all pools.
# Get the raw trade events in pandas
# Note the pool argument must be provided in remote settings
agent_trade_events = agent0.get_trade_events(pool=hyperdrive_pool)
# Gets all open positions and their corresponding PNL for an agent across all pools
agent_positions = agent0.get_positions(pool_filter=hyperdrive_pool)
# Gets all open and closed positions and their corresponding PNL for an agent across all pools
agent_positions = agent0.get_positions(pool_filter=hyperdrive_pool, show_closed_positions=True)

# %% [markdown]
#####################
# Cleanup
#####################
# %%
# Cleanup resources
chain.cleanup()
