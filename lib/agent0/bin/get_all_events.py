"""Script for gathering all events emitted from the hyperdrive contract since the beginning of the chain."""
import pandas as pd
from ethpy.hyperdrive.api import HyperdriveInterface

# TODO parameterize this if we're trying to connect to something other than local chain
hyperdrive = HyperdriveInterface()

# Get all event objects from the contract
hyperdrive_event_objs = hyperdrive.hyperdrive_contract.events

# Get all event classes from the contract's events
hyperdrive_events = [event for key, event in hyperdrive_event_objs.__dict__.items() if key not in ("abi", "_events")]

# Iterate through each event class and get previous logs for each event
# This is meant to be a standalone script, no need for global upper_case naming style
out_events = []  # pylint: disable=invalid-name
for event_obj in hyperdrive_events:
    events = event_obj.get_logs(fromBlock=1)
    # Parse through event data into dict
    for event in events:
        parsed_event = {
            "block_number": event["blockNumber"],
            "event": event["event"],
            "args": dict(event["args"]),
        }
        out_events.append(parsed_event)

# Convert to pandas for postprocessing
out_events = pd.DataFrame(out_events)
out_events = out_events.sort_values("block_number")

# Write to csv
out_events.to_csv("all_events.csv", index=False)
