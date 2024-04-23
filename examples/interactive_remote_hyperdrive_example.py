"""Example script for using interactive hyperdrive to connect to a remote chain.
"""

# %%
# Variables by themselves print out dataframes in a nice format in interactive mode
# pylint: disable=pointless-statement
# We expect this to be a script, hence no need for uppercase naming
# pylint: disable=invalid-name

from fixedpointmath import FixedPoint

from agent0 import IChain, IHyperdrive, PolicyZoo
from agent0.core.base.make_key import make_private_key

# %%
# Set the rpc_uri to the chain, e.g., to sepolia testnet
rpc_uri = "http://uri.to.sepolia.testnet"
chain = IChain(rpc_uri)

# Set the address of the hyperdrive pool
# hyperdrive_address = "0x0000000000000000000000000000000000000000"

# Alternatively, look up the list of registered hyperdrive pools
# This is the registry address deployed on sepolia.
registry_address = "0xba5156E697d39a03EDA824C19f375383F6b759EA"

hyperdrive_address = IHyperdrive.get_hyperdrive_addresses_from_registry(registry_address, chain)["sdai_14_day"]
hyperdrive_config = IHyperdrive.Config()
hyperdrive_pool = IHyperdrive(chain, hyperdrive_address, hyperdrive_config)

# %%

# We set the private key here. In practice, this would be in a private
# env file somewhere, and we only access this through environment variables.
# For now, we generate a random key and explicitly fund it
private_key = make_private_key()

# Init from private key and attach policy
# This ties the hyperdrive_agent to the hyperdrive_pool here.
# We can connect to another hyperdrive pool and create a separate
# agent object using the same private key, but the underlying wallet
# object would then be out of date if both agents are making trades.
# TODO add registry of public key to the chain object, preventing this from happening
hyperdrive_agent0 = hyperdrive_pool.init_agent(
    private_key=private_key,
    policy=PolicyZoo.random,
    # The configuration for the underlying policy
    policy_config=PolicyZoo.random.Config(rng_seed=123),
)

# %%
# We expose this function for testing purposes, but the underlying function calls `mint` and `anvil_set_balance`,
# which are likely to fail on any non-test network.
hyperdrive_agent0.add_funds(base=FixedPoint(100000), eth=FixedPoint(100))

# Set max approval
hyperdrive_agent0.set_max_approval()

# %%

# Make trades
# Return values here mirror the various events emitted from these contract calls
# These functions are blocking, but relatively easy to expose async versions of the
# trades below
open_long_event = hyperdrive_agent0.open_long(base=FixedPoint(11111))
close_long_event = hyperdrive_agent0.close_long(
    maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
)


# %%
random_trade_events = []
for i in range(10):
    # NOTE Since a policy can execute multiple trades per action, the output events is a list
    trade_events: list = hyperdrive_agent0.execute_policy_action()
    random_trade_events.extend(trade_events)
