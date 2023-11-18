import datetime

import pandas as pd
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.state import Long

# TODO change this to be a test
if __name__ == "__main__":
    # Parameters for local chain initialization
    local_chain_config = LocalChain.Config(
        block_time=None,  # If None, mines per transaction. Otherwise mines every `block_time` seconds.
        block_timestamp_interval=None,  # Number of seconds to advance time for every mined block. Uses real time if None.
    )
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

    # Parameters for pool initialization. If empty, defaults to default values, allows for custom values if needed
    initial_pool_config = InteractiveHyperdrive.Config()
    # Launches 2 pools on the same local chain
    interactive_hyperdrive = InteractiveHyperdrive(initial_pool_config, chain)
    interactive_hyperdrive_2 = InteractiveHyperdrive(initial_pool_config, chain)

    # Generate funded trading agents from the interactive object
    # Names are reflected on output data frames and plots later
    hyperdrive_agent0 = interactive_hyperdrive.init_agent(eth=FixedPoint(100), base=FixedPoint(100000), name="alice")
    hyperdrive_agent1 = interactive_hyperdrive.init_agent(eth=FixedPoint(100), base=FixedPoint(100000), name="bob")
    # Omission of name defaults to wallet address
    hyperdrive_agent2 = interactive_hyperdrive.init_agent(eth=FixedPoint(100), base=FixedPoint(100000))

    # Add funds to an agent
    hyperdrive_agent0.add_funds(eth=FixedPoint(100), base=FixedPoint(100000))

    # Here, we execute a trade, where it's calling agent0 + gather data from data pipeline
    # under the hood to allow for error handling and data management
    # Return values here mirror the various events emitted from these contract calls
    open_long_event_1 = hyperdrive_agent0.open_long(base=FixedPoint(11111))

    # Allow for creating checkpoints on the fly
    # TODO double check we can do this in hyperdrive
    checkpoint_event = hyperdrive_agent0.create_checkpoint()

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
        maturity_time=open_long_event_1.maturity_time, bonds=open_long_event_1.balance
    )

    # TODO `agent0/hyperdrive/state/hyperdrive_wallet` needs to add a `maturity_time` field to the object
    agent0_longs: list[Long] = hyperdrive_agent0.wallet.longs.values()
    close_long_event_2 = hyperdrive_agent0.close_long(
        maturity_time=agent0_longs[0].maturity_time, bonds=agent0_longs[0].balance
    )

    # Shorts
    short_event = hyperdrive_agent1.open_short(bonds=FixedPoint(33333))
    hyperdrive_agent1.close_short(maturity_time=short_event.maturity_time, bonds=short_event.balance)

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
