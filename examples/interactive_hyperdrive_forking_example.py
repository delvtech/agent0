"""Example script for using interactive hyperdrive to fork a remote chain.
"""

# %%
# We expect this to be a script, hence no need for uppercase naming
# pylint: disable=invalid-name

from __future__ import annotations

from fixedpointmath import FixedPoint

from agent0 import Hyperdrive, LocalChain, PolicyZoo
from agent0.core.base.make_key import make_private_key

# %%

# The chain to fork, e.g., to sepolia testnet
rpc_uri = "http://uri.to.sepolia.testnet"
# The block number to fork at. If None, will fork at latest.
fork_block_number: int | None = None
# The address of the registry on the chain to find the deployed hyperdrive pool.
registry_address = "0xba5156E697d39a03EDA824C19f375383F6b759EA"

# %%
# Launch a local anvil chain forked from the rpc uri.
chain = LocalChain(fork_uri=rpc_uri, fork_block_number=fork_block_number)

hyperdrive_address = Hyperdrive.get_hyperdrive_addresses_from_registry(chain, registry_address)["sdai_14_day"]

# Note that we use Hyperdrive here instead of LocalHyperdrive,
# as LocalHyperdrive deploys a new pool, whereas we want to connect to an existing pool
# on the forked local chain.
# TODO this prevents us from using data tools provided by LocalHyperdrive, ideally we can
# load a LocalHyperdrive from an Hyperdrive object that connects to an existing pool and populates
# the database. This is blocked by needing an archive node, the fix here would be to
# (1) use event data instead, and (2) build historical data from event data.
hyperdrive_config = Hyperdrive.Config()
hyperdrive_pool = Hyperdrive(chain, hyperdrive_address, hyperdrive_config)

# %%

# Launch a new agent
private_key = make_private_key()

# Init from private key and attach policy
hyperdrive_agent0 = hyperdrive_pool.init_agent(
    private_key=private_key,
    policy=PolicyZoo.random,
    # The configuration for the underlying policy
    policy_config=PolicyZoo.random.Config(rng_seed=123),
)

# %%
# We add funds to the agent.
# TODO this will likely fail when we fork from mainnet, as we call `mint`
# on the base token. This will work on testnet, as we allow minting on the testnet
# base token.
hyperdrive_agent0.add_funds(base=FixedPoint(1000), eth=FixedPoint(100))

# Set max approval
hyperdrive_agent0.set_max_approval()

# %%

# Make trades
# Return values here mirror the various events emitted from these contract calls
# These functions are blocking, but relatively easy to expose async versions of the
# trades below
open_long_event = hyperdrive_agent0.open_long(base=FixedPoint(111))
close_long_event = hyperdrive_agent0.close_long(
    maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount
)


# %%
random_trade_events = []
for i in range(10):
    # NOTE Since a policy can execute multiple trades per action, the output events is a list
    trade_events: list = hyperdrive_agent0.execute_policy_action()
    random_trade_events.extend(trade_events)
