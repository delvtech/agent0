"""Example script for using interactive hyperdrive."""
# %%
import datetime

from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain

# %%
# Parameters for local chain initialization, defines defaults in constructor
local_chain_config = LocalChain.Config()
# Launches a local chain in a subprocess
# This also launches a local postgres docker container for data under the hood, attached to the chain.
# Each hyperdrive pool will have it's own database within this container
# NOTE: LocalChain is a subclass of Chain
# TODO can also implement functionality such as save/load state here
chain = LocalChain(local_chain_config)
# Can connect to a specific existing chain
# existing_chain = Chain("http://localhost:8545")

# Initialize the interactive object with specified initial pool parameters and the chain to launch hyperdrive on
# An "admin" user (as provided by the Chain object) is launched/funded here for deploying hyperdrive

# %%
# Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
initial_pool_config = InteractiveHyperdrive.Config()
# Launches 2 pools on the same local chain
interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)
interactive_hyperdrive_2 = InteractiveHyperdrive(chain, initial_pool_config)

# %%
# Generate funded trading agents from the interactive object
# Names are reflected on output data frames and plots later
hyperdrive_agent0 = interactive_hyperdrive.init_agent(base=FixedPoint(100000), eth=FixedPoint(100), name="alice")
hyperdrive_agent1 = interactive_hyperdrive_2.init_agent(base=FixedPoint(100000), eth=FixedPoint(100), name="bob")
# Omission of name defaults to wallet address
hyperdrive_agent2 = interactive_hyperdrive.init_agent(base=FixedPoint(100000))

# Add funds to an agent
hyperdrive_agent0.add_funds(base=FixedPoint(100000), eth=FixedPoint(100))

# %%
# Here, we execute a trade, where it's calling agent0 + gather data from data pipeline
# under the hood to allow for error handling and data management
# Return values here mirror the various events emitted from these contract calls
open_long_event_1 = hyperdrive_agent0.open_long(base=FixedPoint(11111))

# Allow for creating checkpoints on the fly
# TODO Need to figure out how to mint checkpoints on the fly
# checkpoint_event = hyperdrive_agent0.create_checkpoint()

# Another long with a different maturity time
open_long_event_2 = hyperdrive_agent0.open_long(FixedPoint(22222))

# View current wallet
print(hyperdrive_agent0.wallet)

# NOTE these calls are chainwide calls, so all pools connected to this chain gets affected.
# Advance time, accepts timedelta or seconds
chain.advance_time(datetime.timedelta(weeks=52))
chain.advance_time(3600)

# Close previous longs
close_long_event_1 = hyperdrive_agent0.close_long(
    maturity_time=open_long_event_1.maturity_time, bonds=open_long_event_1.bond_amount
)

agent0_longs = list(hyperdrive_agent0.wallet.longs.values())
close_long_event_2 = hyperdrive_agent0.close_long(
    maturity_time=agent0_longs[0].maturity_time, bonds=agent0_longs[0].balance
)

# Shorts
open_short_event = hyperdrive_agent1.open_short(bonds=FixedPoint(33333))
close_short_event = hyperdrive_agent1.close_short(
    maturity_time=open_short_event.maturity_time, bonds=open_short_event.bond_amount
)

# LP
add_lp_event = hyperdrive_agent2.add_liquidity(base=FixedPoint(44444))
# Add a long to ensure there are withdraw shares to withdraw
open_long_event = hyperdrive_agent2.open_long(base=FixedPoint(55555))
remove_lp_event = hyperdrive_agent2.remove_liquidity(shares=hyperdrive_agent2.wallet.lp_tokens)
# Close the long to ensure the withdrawal share is ready to withdraw
hyperdrive_agent2.close_long(maturity_time=open_long_event.maturity_time, bonds=open_long_event.bond_amount)
withdraw_shares_event = hyperdrive_agent2.redeem_withdraw_share(shares=hyperdrive_agent2.wallet.withdraw_shares)

# %%
# Get data from database under the hood
# TODO: https://github.com/delvtech/agent0/issues/1106
pool_config = interactive_hyperdrive.get_pool_config()
pool_info_history = interactive_hyperdrive.get_pool_info()
# TODO checkpoint info is currently bugged, fix
checkpoint_info = interactive_hyperdrive.get_checkpoint_info()
pool_analysis = interactive_hyperdrive.get_pool_analysis()
wallet_positions = interactive_hyperdrive.get_wallet_positions(coerce_float=False)
current_wallet = interactive_hyperdrive.get_current_wallet()
ticker = interactive_hyperdrive.get_ticker()
total_wallet_pnl_over_time = interactive_hyperdrive.get_total_wallet_pnl_over_time()

# %%

# Plot pretty plots
# TODO these should be in a notebook for plotting
pool_info_history.plot(x="timestamp", y="longs_outstanding", kind="line")
# Change wallet_address to be columns for plotting
total_wallet_pnl_over_time.pivot(index="timestamp", columns="wallet_address", values="pnl").plot()
