"""Example script for using interactive hyperdrive to fork a remote chain.
"""

# %%
# We expect this to be a script, hence no need for uppercase naming
# pylint: disable=invalid-name

from __future__ import annotations

from fixedpointmath import FixedPoint

from agent0 import LocalChain, LocalHyperdrive, PolicyZoo
from agent0.core.base.make_key import make_private_key

# %%
NUM_TEST_TRADES = 10

# The chain to fork, e.g., to sepolia testnet
rpc_uri = "http://uri.to.sepolia.testnet"
# The block number to fork at. If None, will fork at latest.
fork_block_number: int | None = None
# The address of the registry on the chain to find the deployed hyperdrive pool.
registry_address = "0xba5156E697d39a03EDA824C19f375383F6b759EA"

# %%
# Launch a local anvil chain forked from the rpc uri.
chain = LocalChain(fork_uri=rpc_uri, fork_block_number=fork_block_number)

hyperdrive_address = LocalHyperdrive.get_hyperdrive_addresses_from_registry(chain, registry_address)["sdai_14_day"]

# Note that we pass in deploy=False and pass in an existing hyperdrive_address, as we
# want to connect to the existing pool and not deploy a new one.
hyperdrive_config = LocalHyperdrive.Config()
hyperdrive_pool = LocalHyperdrive(chain, hyperdrive_config, deploy=False, hyperdrive_address=hyperdrive_address)

# %%

# Launch a new agent
private_key = make_private_key()

# Init from private key and attach policy
hyperdrive_agent0 = chain.init_agent(
    private_key=private_key,
    pool=hyperdrive_pool,
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
for i in range(NUM_TEST_TRADES):
    # NOTE Since a policy can execute multiple trades per action, the output events is a list
    trade_events: list = hyperdrive_agent0.execute_policy_action()
    random_trade_events.extend(trade_events)
