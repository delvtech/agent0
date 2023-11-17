import pandas as pd
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InitialPool, InteractiveHyperdrive

# Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
initial_pool_config = InitialPool()

# Initialize the interactive object with specified initial pool parameters
# This launches a local chain in a subprocess (or docker) and a database
hyperdrive_agent0 = InteractiveHyperdrive(initial_pool_config)
# One agent is created and funded ready to go, likely using something similar to the "deterministic" policy

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
pool_info_history: pd.DataFrame = hyperdrive_agent0.get_pool_info_history()

# Plot pretty plots
pool_info_history.plot(x="block_time", y="outstanding_longs", kind="line")
