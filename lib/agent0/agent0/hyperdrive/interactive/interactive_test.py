from typing import TYPE_CHECKING

import pandas as pd
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InitialPoolConfig, InteractiveHyperdrive
from agent0.hyperdrive.state import Long, Short

# Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
initial_pool_config = InitialPoolConfig()

# Initialize the interactive object with specified initial pool parameters
# This launches a local chain in a subprocess (or docker) and a database
# A "admin" user is launched/funded here for deploying hyperdrive
interactive_hyperdrive = InteractiveHyperdrive(initial_pool_config)

# Generate funded trading agents from the interactive object
# Names are reflected on output data frames and plots later
hyperdrive_agent0 = interactive_hyperdrive.init_agent(eth=FixedPoint(100), base=FixedPoint(100000), name="alice")
hyperdrive_agent1 = interactive_hyperdrive.init_agent(eth=FixedPoint(100), base=FixedPoint(100000), name="bob")
# Omission of name defaults to wallet address
hyperdrive_agent2 = interactive_hyperdrive.init_agent(eth=FixedPoint(100), base=FixedPoint(100000))

# Here, we execute a trade, where it's calling agent0 + gather data from data pipeline
# under the hood to allow for error handling and data management
# Return values here mirror the various events emitted from these contract calls
open_long_event_1 = hyperdrive_agent0.open_long(base=FixedPoint(11111))

# Allow for creating checkpoints on the fly
checkpoint_event = hyperdrive_agent0.create_checkpoint()

# Another long with a different maturity time
open_long_event_2 = hyperdrive_agent0.open_long(FixedPoint(22222))

# View current wallet
print(hyperdrive_agent0.wallet)

# Close previous longs
close_long_event_1 = hyperdrive_agent0.close_long(
    maturity_time=open_long_event_1.maturity_time, bonds=open_long_event_1.value
)

# Proposing for the longs/shorts here to be a list of data classes
# Easiest way forward here is for the Long/Short class to in
# `agent0/hyperdrive/state/hyperdrive_wallet` to add a `maturity_time`
# field and build from the underlying dict -> list on this call
agent0_longs: list[Long] = hyperdrive_agent0.wallet.longs
close_long_event_2 = hyperdrive_agent0.close_long(
    maturity_time=agent0_longs[0].maturity_time, bonds=agent0_longs[0].balance
)

# Shorts
short_event = hyperdrive_agent1.open_short(bonds=FixedPoint(33333))
hyperdrive_agent1.close_short(maturity_time=short_event.maturity_time, bonds=short_event.value)

# LP
add_lp_event = hyperdrive_agent2.add_liquidity(base=FixedPoint(44444))
remove_lp_event = hyperdrive_agent2.remove_liquidity(bonds=hyperdrive_agent2.wallet.lp_tokens)
withdraw_shares_event = hyperdrive_agent2.redeem_withdraw_shares(shares=hyperdrive_agent2.wallet.withdraw_shares)


# Get data from database under the hood
pool_info_history: pd.DataFrame = interactive_hyperdrive.get_pool_info()
wallet_positions: pd.DataFrame = interactive_hyperdrive.get_current_wallet()
wallet_pnls: pd.DataFrame = interactive_hyperdrive.get_wallet_pnl()

# Plot pretty plots
pool_info_history.plot(x="block_time", y="outstanding_longs", kind="line")
wallet_pnls.plot()
