"""Get the number of the block that is at or immediately before the given timestamp."""

from __future__ import annotations

from eth_typing import BlockNumber
from web3 import Web3
from web3.types import Timestamp

# pylint: disable=too-many-locals


def block_number_before_timestamp(web3: Web3, block_timestamp: Timestamp | int) -> BlockNumber:
    """Finds the closest block number that is before or at the given block time.

    Arguments
    ---------
    web3: Web3
        The web3 instance.
    block_timestamp: BlockTime | int
        The block time to find the closest block to.

    Returns
    -------
    BlockNumber
        The closest block number to the given block time.
    """
    # Get the current block number and timestamp
    block_timestamp = Timestamp(block_timestamp)
    current_block = web3.eth.get_block("latest")
    current_block_number = current_block.get("number", None)
    assert current_block_number is not None
    if current_block_number < 3:
        raise ValueError("The current block number must be >= 2.")
    current_block_timestamp = current_block.get("timestamp", None)
    assert current_block_timestamp is not None

    # Estimate the average block time
    earlier_block_number = current_block_number // 2
    earlier_block_delta = current_block_number - earlier_block_number
    if earlier_block_delta <= 0:
        raise ValueError("Error estimating the delta blocks.")
    earlier_block_timestamp = web3.eth.get_block(earlier_block_number).get("timestamp", None)
    assert earlier_block_timestamp is not None
    avg_time_between_blocks = (current_block_timestamp - earlier_block_timestamp) / earlier_block_delta

    # Estimate the block number corresponding to the user provided timestamp
    delta_time = current_block_timestamp - block_timestamp
    estimated_block_number = current_block_number - (delta_time // avg_time_between_blocks)

    # Establish upper and lower bounds
    left = int(max(0, estimated_block_number - 100))  # search 100 blocks before estimated block
    right = int(min(current_block_number, estimated_block_number + 100))  # search 100 blocks after estimated block

    # Ensure bounds of binary search is within the target timestamp
    left_timestamp = web3.eth.get_block(left).get("timestamp", None)
    assert left_timestamp is not None
    if left_timestamp > block_timestamp:
        left = 0
    right_timestamp = web3.eth.get_block(right).get("timestamp", None)
    assert right_timestamp is not None
    if right_timestamp < block_timestamp:
        right = current_block_number

    # Use a binary search to find the block
    while left <= right:
        mid = int((left + right) // 2)
        block = web3.eth.get_block(BlockNumber(mid))
        search_block_timestamp = block.get("timestamp", None)
        assert search_block_timestamp is not None
        if search_block_timestamp > block_timestamp:
            # The mid point is later than the block we want, set right to mid-1
            right = mid - 1
        elif search_block_timestamp < block_timestamp:
            # The mid point is earlier than the block we want
            # The user could enter a time that is greater than the nearest block
            # timestamp but less than the next block timestamp
            next_block = web3.eth.get_block(BlockNumber(mid + 1))
            next_block_timestamp = next_block.get("timestamp", None)
            assert next_block_timestamp is not None
            if next_block_timestamp > block_timestamp:
                # The user time is between the current and next block
                return BlockNumber(mid)
            # If the next block wasn't right, then set it to left
            left = mid + 1
        else:
            # The mid point is the right block
            return BlockNumber(mid)
    return BlockNumber(left)
