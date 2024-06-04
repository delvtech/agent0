"""An example of using agent0 to execute or analyze trades on a remote chain."""

# %% [markdown]
# This example demonstrates how to connect to a remote chain for analysis.
# It is a demo, however, so we will spoof a remote chain using similar steps to the local hyperdrive example.

# %% [markdown]
#####################
# Initialization
#####################

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
# In a typical remote setup we would want to set the rpc_uri to a remote chain,
# such as Sepolia testnet:
# rpc_uri = "http://uri.to.sepolia.testnet"
# hyperdrive_address = "0x0000000000000000000000000000000000000000"

# In addition to explicitly defining a contract address, we can also query the deployed registry to
# look up registered hyperdrive pools. For example, we can define the registry address on Sepolia testnet,
# then query it for the list of registered pools:
# registry_address = "0xba5156E697d39a03EDA824C19f375383F6b759EA"
# hyperdrive_address = Hyperdrive.get_hyperdrive_addresses_from_registry(chain, registry_address)["sdai_14_day"]

# For this example, we instead launch a chain and local hyperdrive, and connect the remote chains to these resources.
local_chain = LocalChain()
local_hyperdrive = LocalHyperdrive(local_chain)
rpc_uri = local_chain.rpc_uri
hyperdrive_address = local_hyperdrive.hyperdrive_address


# Now we can treat the above as a remote chain and pool for our demonstration
# NOTE: Need to set different db port here to avoid port collisions with local chain.
chain = Chain(rpc_uri, config=Chain.Config(db_port=1234))
hyperdrive_config = Hyperdrive.Config()
hyperdrive_pool = Hyperdrive(chain, hyperdrive_address, hyperdrive_config)

# %%

# Initialize agents:

# We set the private key here. In practice, this would be in a private
# env file somewhere, and we only access this through environment variables.
# For now, we generate a random key and explicitly fund it.
private_key_0 = make_private_key()
private_key_1 = make_private_key()

# Init from private key
agent0 = chain.init_agent(
    private_key=private_key_0,
    name="agent0",
)
# We can initialize an agent with an active policy - more on that later.
agent1 = chain.init_agent(
    private_key=private_key_1,
    name="agent1",
    policy=PolicyZoo.random,
    policy_config=PolicyZoo.random.Config(),
)

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
agent0.set_max_approval(pool=hyperdrive_pool)
agent1.set_max_approval()

# %%
# The return values for trade functions mirror the various events emitted from these contract calls
# Here, base is unitless and is dependent on the underlying tokens the pool uses.
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
# These functions query the underlying database to get data.
# All functions here return a Pandas dataframe.

# Get the raw trade events for the pool.
# Note the pool argument must be provided in remote settings.
agent_trade_events = agent0.get_trade_events(pool_filter=hyperdrive_pool)
# Gets all open positions and their corresponding PNL for an agent for the pool.
agent_positions = agent0.get_positions(pool_filter=hyperdrive_pool)
# Gets all open and closed positions and their corresponding PNL for an agent for the pool.
agent_positions = agent0.get_positions(pool_filter=hyperdrive_pool, show_closed_positions=True)

# %% [markdown]
#####################
# Cleanup
#####################
# %%
# Cleanup resources
chain.cleanup()
