"""Script for gathering all events emitted from the hyperdrive contract since the beginning of the chain."""
import pandas as pd
from chainsync.db.hyperdrive import get_transactions
from fixedpointmath import FixedPoint

from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.hyperdrive.policies import Zoo

# This is meant to be a standalone script, no need for global upper_case naming style
# pylint: disable=invalid-name

local_chain_config = LocalChain.Config()
chain = LocalChain(local_chain_config)
initial_pool_config = InteractiveHyperdrive.Config()
interactive_hyperdrive = InteractiveHyperdrive(chain, initial_pool_config)
interactive_hyperdrive2 = InteractiveHyperdrive(chain, initial_pool_config)
interactive_hyperdrive3 = InteractiveHyperdrive(chain, initial_pool_config)

# %%
# Generate funded trading agents from the interactive object
# Names are reflected on output data frames and plots later
hyperdrive_agent0 = interactive_hyperdrive.init_agent(
    base=FixedPoint(100000), eth=FixedPoint(100), name="alice", policy=Zoo.random
)
hyperdrive_agent1 = interactive_hyperdrive2.init_agent(
    base=FixedPoint(100000), eth=FixedPoint(100), name="bob", policy=Zoo.random
)
# Omission of name defaults to wallet address
hyperdrive_agent2 = interactive_hyperdrive2.init_agent(
    base=FixedPoint(100000), eth=FixedPoint(100), name="bob", policy=Zoo.random
)

for _ in range(10):
    hyperdrive_agent0.execute_policy_action()
    hyperdrive_agent1.execute_policy_action()
    hyperdrive_agent2.execute_policy_action()

chain.advance_time(5000, create_checkpoints=True)

for _ in range(10):
    hyperdrive_agent0.execute_policy_action()
    hyperdrive_agent1.execute_policy_action()
    hyperdrive_agent2.execute_policy_action()

out_events = []
out_transactions = []
for i_hd in [interactive_hyperdrive, interactive_hyperdrive2, interactive_hyperdrive3]:
    hyperdrive = i_hd.hyperdrive_interface

    # Get all event objects from the contract
    hyperdrive_event_objs = hyperdrive.hyperdrive_contract.events

    # Get all event classes from the contract's events
    hyperdrive_events = [
        event for key, event in hyperdrive_event_objs.__dict__.items() if key not in ("abi", "_events")
    ]

    # Iterate through each event class and get previous logs for each event
    for event_obj in hyperdrive_events:
        events = event_obj.get_logs(fromBlock=0)
        # Parse through event data into dict
        for event in events:
            parsed_event = {
                "block_number": event["blockNumber"],
                "hyperdrive_contract_address": i_hd.hyperdrive_interface.hyperdrive_contract.address,
                "event": event["event"],
                "args": dict(event["args"]),
            }
            out_events.append(parsed_event)

    # Get transaction hash
    txns = get_transactions(i_hd.db_session)
    out_transactions.append(txns[["transaction_hash", "block_number", "input_method"]])

chain.cleanup()

# Convert to pandas for postprocessing
out_events = pd.DataFrame(out_events)
out_events = out_events.sort_values("block_number")
out_transactions = pd.concat(out_transactions, axis=0).sort_values("block_number")

# Write to csv
out_events.to_csv("all_events.csv", index=False)
out_transactions.to_csv("all_transactions.csv", index=False)
