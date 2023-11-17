import pandas as pd
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InitialPoolConfig, InteractiveHyperdrive

# Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
initial_pool_config = InitialPoolConfig()

# Initialize the interactive object with specified initial pool parameters
# This launches a local chain in a subprocess (or docker) and a database
# A "admin" user is launched/funded here for deploying hyperdrive
interactive_hyperdrive = InteractiveHyperdrive(initial_pool_config)

# Generate funded trading agents from the interactive object
hyperdrive_agent0 = interactive_hyperdrive.init_agent(eth=FixedPoint(100), base=FixedPoint(100000))
hyperdrive_agent1 = interactive_hyperdrive.init_agent(eth=FixedPoint(100), base=FixedPoint(100000))

# Here, we execute a trade, where it's calling agent0 + gather data from data pipeline
# under the hood to allow for error handling and data management
# Return values here mirror the various events emitted from these contract calls
long_event_1 = hyperdrive_agent0.open_long(FixedPoint(1000))

# Allow for creating checkpoints on the fly
checkpoint_event = hyperdrive_agent0.create_checkpoint()

# Another long with a different maturity time
long_event_2 = hyperdrive_agent0.open_long(FixedPoint(2000))

# View current wallet
print(hyperdrive_agent0.wallet)

# Close previous longs
hyperdrive_agent0.close_long(maturity_time=long_event_1.maturity_time, value=long_event_1.value)

# Get data from database under the hood
pool_info_history: pd.DataFrame = interactive_hyperdrive.get_pool_info_history()

# Plot pretty plots
pool_info_history.plot(x="block_time", y="outstanding_longs", kind="line")
