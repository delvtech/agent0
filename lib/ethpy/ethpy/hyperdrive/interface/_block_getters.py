"""Getter functions for the RPI block."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from eth_typing import BlockNumber
    from web3.types import BlockData, BlockIdentifier, Timestamp

    from .read_interface import HyperdriveReadInterface


def _get_block(interface: HyperdriveReadInterface, block_identifier: BlockIdentifier) -> BlockData:
    """See API for documentation."""
    return interface.web3.eth.get_block(block_identifier)


def _get_block_number(block: BlockData) -> BlockNumber:
    """See API for documentation."""
    block_number = block.get("number", None)
    if block_number is None:
        raise AssertionError("The provided block has no number")
    return block_number


def _get_block_time(block: BlockData) -> Timestamp:
    """See API for documentation."""
    block_timestamp = block.get("timestamp", None)
    if block_timestamp is None:
        raise AssertionError("The provided block has no timestamp")
    return block_timestamp


def _get_checkpoint_id(interface, block_timestamp: Timestamp) -> Timestamp:
    """See API for documentation."""
    latest_checkpoint_timestamp = block_timestamp - (block_timestamp % interface.pool_config["checkpointDuration"])
    return cast(Timestamp, latest_checkpoint_timestamp)
