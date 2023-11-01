"""Getter functions for the RPI block."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from eth_typing import BlockNumber
    from web3.types import BlockData, BlockIdentifier, Timestamp

    from .api import HyperdriveInterface


def _get_block(
    cls: HyperdriveInterface, block_identifier: BlockIdentifier
) -> BlockData:
    """Returns the block specified by block_identifier.

    Delegates to eth_getBlockByNumber if block_identifier is an integer or
    one of the predefined block parameters 'latest', 'earliest', 'pending', 'safe', 'finalized'.
    Otherwise delegates to eth_getBlockByHash.
    Throws BlockNotFound error if the block is not found.
    """
    return cls.web3.eth.get_block(block_identifier)


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


def _get_checkpoint_id(cls, block_timestamp: Timestamp) -> Timestamp:
    """See API for documentation."""
    latest_checkpoint_timestamp = block_timestamp - (
        block_timestamp % cls.pool_config["checkpointDuration"]
    )
    return cast(Timestamp, latest_checkpoint_timestamp)
