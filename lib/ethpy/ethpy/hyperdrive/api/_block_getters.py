"""Getter functions for the RPI block."""
from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from eth_typing import BlockNumber
    from web3.types import BlockData, BlockIdentifier, Timestamp

    from .api import HyperdriveInterface


def _get_block(cls: HyperdriveInterface, block_identifier: BlockIdentifier) -> BlockData:
    """Returns the block specified by block_identifier.

    Delegates to eth_getBlockByNumber if block_identifier is an integer or
    one of the predefined block parameters 'latest', 'earliest', 'pending', 'safe', 'finalized'.
    Otherwise delegates to eth_getBlockByHash.
    Throws BlockNotFound error if the block is not found.
    """
    return cls.web3.eth.get_block(block_identifier)


def _get_block_number(cls: HyperdriveInterface, block_identifier: BlockIdentifier) -> BlockNumber:
    """See API for documentation."""
    current_block_number = _get_block(cls, block_identifier).get("number", None)
    if current_block_number is None:
        raise AssertionError("The current block has no number")
    return current_block_number


def _get_block_time(cls: HyperdriveInterface, block_identifier: BlockIdentifier) -> Timestamp:
    """See API for documentation."""
    current_block_timestamp = _get_block(cls, block_identifier).get("timestamp", None)
    if current_block_timestamp is None:
        raise AssertionError("current_block_timestamp can not be None")
    return current_block_timestamp


def _get_checkpoint_id(cls, block_timestamp: Timestamp) -> Timestamp:
    """See API for documentation."""
    latest_checkpoint_timestamp = block_timestamp - (block_timestamp % cls.pool_config["checkpointDuration"])
    return cast(Timestamp, latest_checkpoint_timestamp)
