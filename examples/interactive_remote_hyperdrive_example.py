"""Example script for using interactive hyperdrive to connect to a remote chain.
"""

# %%
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement
# We expect this to be a script, hence no need for uppercase naming
# pylint: disable=invalid-name

from fixedpointmath import FixedPoint

from agent0 import Chain, Hyperdrive, PolicyZoo
from agent0.core.base.make_key import make_private_key

# %% [markdown]
#####################
# Initialization
#####################

# %%
# Set the rpc_uri to the chain, e.g., to sepolia testnet
rpc_uri = "http://uri.to.sepolia.testnet"
chain = Chain(rpc_uri)

# %%

# We set the private key here. In practice, this would be in a private
# env file somewhere, and we only access this through environment variables.
# For now, we generate a random key and explicitly fund it
private_key_0 = make_private_key()
private_key_1 = make_private_key()

# Init from private key
agent0 = chain.init_agent(
    private_key=private_key_0,
)
agent1 = chain.init_agent(
    private_key=private_key_1,
)

# %%
# We expose this function for testing purposes, but the underlying function
# calls `mint` and `anvil_set_balance`, which are likely to fail on any non-test
# network. In practice, it's up to the user to ensure the wallet has sufficient funds.
agent0.add_funds(base=FixedPoint(100000), eth=FixedPoint(100))
agent1.add_funds(base=FixedPoint(100000), eth=FixedPoint(100))

# %%
# Connect to a hyperdrive pool

# Define a specific pool address
# hyperdrive_address = "0x0000000000000000000000000000000000000000"

# Alternatively, look up the list of registered hyperdrive pools
# This is the registry address deployed on sepolia.
registry_address = "0xba5156E697d39a03EDA824C19f375383F6b759EA"

hyperdrive_address = Hyperdrive.get_hyperdrive_addresses_from_registry(chain, registry_address)["sdai_14_day"]
hyperdrive_config = Hyperdrive.Config()
hyperdrive_pool = Hyperdrive(chain, hyperdrive_address, hyperdrive_config)

# %% [markdown]
#####################
# Executing Trades
#####################

# We set agent1's active pool to avoid passing in pool for functions.
agent1.set_active_pool(pool=hyperdrive_pool)

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

# NOTE:
# Best practices for policies include creating a separate policy object for each agent and pool the policy
# is expect to run on. This ensures that any internal state the policy uses is tied to a single agent and pool
# (which most of our existing policies assume). This isn't strictly necessary for e.g., `RandomPolicy`,
# which doesn't use state as bookkeeping (and it even may be desired to use a single policy object to e.g.,
# use one rng state across all trades). Overall, we leave the mapping between policy objects, agents, and pools
# to the specific policy implementation and caller.

random_policy_config = PolicyZoo.random.Config(rng_seed=123)
agent0_random_policy = PolicyZoo.random(random_policy_config)
agent1_random_policy = PolicyZoo.random(random_policy_config)

# Execute policy trade on a pool
# Output event is one of the possible trade events
agent0_trades = []
for i in range(10):
    # NOTE Since a policy can execute multiple trades per action, the output events is a list
    agent0_trades.extend(agent0.execute_policy_action(policy=agent0_random_policy, pool=hyperdrive_pool))

# Similar to pools, we can set an active policy for an agent
agent1.set_active_policy(agent1_random_policy)
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
agent0_wallet = agent0.get_wallet()

# TODO figure out what analysis we want to support wrt a pool for remote connections.
# The data pipeline requires wrt pools requires lots of read calls on an archive node,
# which may be prohibitive.

# %% [markdown]
#####################
# Cleanup
#####################
# %%
# Cleanup resources
chain.cleanup()
