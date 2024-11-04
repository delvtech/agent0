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
    # Use a binary search to match the block time to the block number.
    current_block = web3.eth.get_block("latest")
    current_block_number = current_block.get("number", None)
    assert current_block_number is not None
    current_block_timestamp = current_block.get("timestamp", None)
    assert current_block_timestamp is not None

    # Estimate the average block time
    earlier_block_number = current_block_number // 2
    blocks_skipped = current_block_number - earlier_block_number
    assert blocks_skipped > 0
    earlier_blcok_timestamp = web3.eth.get_block(earlier_block_number).get("timestamp", None)
    assert earlier_blcok_timestamp is not None
    avg_time_between_blocks = (current_block_timestamp - earlier_blcok_timestamp) / blocks_skipped

    # How far back the user wants to search
    delta_time = current_block_timestamp - block_timestamp
    estimated_block_number = current_block_number - (delta_time // avg_time_between_blocks)

    # Use a binary search to find the block
    left = int(max(0, estimated_block_number - 100))  # search 100 blocks before estimated block
    right = int(min(current_block_number, estimated_block_number + 100))  # search 100 blocks after estimated block
    while left <= right:
        mid = int((left + right) // 2)
        block = web3.eth.get_block(BlockNumber(mid))
        search_block_timestamp = block.get("timestamp", None)
        assert search_block_timestamp is not None
        time_error = search_block_timestamp - block_timestamp
        if time_error >= 0:
            left = mid + 1
        else:
            right = mid - 1
    return BlockNumber(left)
