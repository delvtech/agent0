"""Hyperdrive interface functions that get event logs from the chain."""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent0.ethpy.base import EARLIEST_BLOCK_LOOKUP

if TYPE_CHECKING:
    from .read_interface import HyperdriveReadInterface


def _get_pool_is_paused(
    hyperdrive_interface: HyperdriveReadInterface,
) -> bool:
    chain_id = hyperdrive_interface.web3.eth.chain_id
    # If not in lookup, we default to `earliest`
    if chain_id not in EARLIEST_BLOCK_LOOKUP:
        from_block = "earliest"
    else:
        from_block = EARLIEST_BLOCK_LOOKUP[chain_id]

    pause_events = hyperdrive_interface.hyperdrive_contract.events.PauseStatusUpdated.get_logs_typed(
        from_block=from_block
    )
    is_paused = False
    if len(list(pause_events)) > 0:
        # Get the latest pause event
        # TODO get_logs likely returns events in an ordered
        # fashion, but we iterate and find the latest one
        # just in case
        latest_pause_event = None
        max_block_number = 0
        for event in pause_events:
            if event.block_number > max_block_number:
                max_block_number = event.block_number
                latest_pause_event = event
        assert latest_pause_event is not None
        is_paused = latest_pause_event.args.isPaused
    return is_paused
