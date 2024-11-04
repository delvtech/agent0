from eth_typing import BlockNumber
from web3 import Web3
from web3.types import Timestamp


def block_before_timestamp(web3: Web3, block_timestamp: Timestamp | int) -> BlockNumber:
    """Finds the closest block that is before or at the given block time.

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

    # Use a binary search to find the block
    left = int(max(0, estimated_block_number - 100))  # search 100 blocks before estimated block
    right = int(min(current_block_number, estimated_block_number + 100))  # search 100 blocks after estimated block
    while left < right:
        mid = int((left + right) // 2)
        block = web3.eth.get_block(BlockNumber(mid))
        search_block_timestamp = block.get("timestamp", None)
        assert search_block_timestamp is not None
        if search_block_timestamp > block_timestamp:
            # The mid point is later than the block we want
            # The user could enter a time that is greater than the nearest block
            # timestamp but less than the next block timestamp. Therefore, set
            # upper bound to mid.
            right = mid
        elif search_block_timestamp < block_timestamp:
            # The mid point is earlier than the block we want, set lower bound
            # to mid + 1
            left = mid + 1
        else:
            # The mid point is the right block
            return BlockNumber(mid)
    return BlockNumber(left)
