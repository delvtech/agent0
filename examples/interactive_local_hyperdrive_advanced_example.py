"""Example script for using interactive hyperdrive."""

# pylint: disable=pointless-statement
# %%
# Variables by themselves print out dataframes in a nice format in interactive mode

from fixedpointmath import FixedPoint

from agent0 import ILocalChain, ILocalHyperdrive, PolicyZoo

# %%
# Parameters for local chain initialization, defines defaults in constructor
local_chain_config = ILocalChain.Config()
# Launches a local chain in a subprocess
# This also launches a local postgres docker container for data under the hood, attached to the chain.
# Each hyperdrive pool will have it's own database within this container
# NOTE: LocalChain is a subclass of Chain
# TODO can also implement functionality such as save/load state here
chain = ILocalChain(local_chain_config)
# Can connect to a specific existing chain
# existing_chain = Chain("http://localhost:8545")

# %%
# Initialize the interactive object with specified initial pool parameters and the chain to launch hyperdrive on
# An "admin" user (as provided by the Chain object) is launched/funded here for deploying hyperdrive

# Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
initial_pool_config = ILocalHyperdrive.Config()
# Launches 2 pools on the same local chain
interactive_hyperdrive = ILocalHyperdrive(chain, initial_pool_config)

# %%
# Generate funded trading agents from the interactive object
# Names are reflected on output data frames and plots later
hyperdrive_random_agent = interactive_hyperdrive.init_agent(
    base=FixedPoint(100000),
    eth=FixedPoint(100),
    name="random_bot",
    # The underlying policy to attach to this agent
    policy=PolicyZoo.random,
    # The configuration for the underlying policy
    policy_config=PolicyZoo.random.Config(rng_seed=123),
)

# %%
# Saves a snapshot of the state
# NOTE: Due to bookkeeping purposes, some features gets disabled once a snapshot gets made
# i.e., creating new pools, creating new agents, and adding funds.
# Only one snapshot can be saved at a time.
chain.save_snapshot()

# %%
# Loads the snapshot of the state.
chain.load_snapshot()

# %%
# Execute interactive trade
open_long_event_1 = hyperdrive_random_agent.open_long(base=FixedPoint(11111))
open_long_event_1  # pyright: ignore
# %%
# Execute policy trade
# Output event is one of the possible trade events
random_trade_events = []
for i in range(10):
    # NOTE Since a policy can execute multiple trades per action, the output events is a list
    trade_events: list = hyperdrive_random_agent.execute_policy_action()
    random_trade_events.extend(trade_events)
random_trade_events  # pyright: ignore

# %%
# Set the underlying yield variable rate
interactive_hyperdrive.set_variable_rate(FixedPoint("0.10"))

# %%
# Runs the dashboard in blocking mode, which waits for a keyboard press to exit the dashboard
print(interactive_hyperdrive.run_dashboard(blocking=True))

# %%
# cleanup resources
chain.cleanup()
