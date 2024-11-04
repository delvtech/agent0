"""Script to check the ezeth vault share price."""

import argparse
import os

from dotenv import load_dotenv

from agent0 import Chain, Hyperdrive
from agent0.utils import block_number_before_timestamp

load_dotenv(".env")
DEV_RPC_URI = os.getenv("DEV_RPC_URI", "")
RPC_URI = DEV_RPC_URI
REGISTRY_ADDRESS = os.getenv("REGISTRY_ADDRESS", "")


def main(start_block_timestamp: int, lookback_length: int):
    """Main entry point.

    Arguments
    ---------
    start_block_timestamp: int
        The start block timestamp, in seconds (should be after the ezETH Hyperdrive pool was deployed).
    lookback_length: int
        The number of seconds to lookback from the start block.
    """
    with Chain(RPC_URI, config=Chain.Config(no_postgres=True)) as chain:
        # Get the ezeth pool
        registered_pools = Hyperdrive.get_hyperdrive_pools_from_registry(
            chain,
            registry_address=REGISTRY_ADDRESS,
        )
        ezeth_pool = [pool for pool in registered_pools if pool.name == "ElementDAO 182 Day ezETH Hyperdrive"][0]
        web3 = ezeth_pool.interface.web3

        # If the start block is zero, use the current block
        if start_block_timestamp <= 0:
            start_block_timestamp = chain.block_time()
            start_block_number = chain.block_number()
        # Otherwise, find the block with the given blocktime
        else:
            start_block_number = block_number_before_timestamp(web3, start_block_timestamp)

        start_pool_state = ezeth_pool.interface.get_hyperdrive_state(block_identifier=start_block_number)
        start_vault_share_price = start_pool_state.pool_info.vault_share_price

        lookback_timestamp = start_block_timestamp - lookback_length
        lookback_block_number = block_number_before_timestamp(web3, lookback_timestamp)
        lookback_pool_state = ezeth_pool.interface.get_hyperdrive_state(block_identifier=lookback_block_number)
        lookback_vault_share_price = lookback_pool_state.pool_info.vault_share_price

    print(
        f"Calculating vault share price difference between block {start_block_number} and block {lookback_block_number}"
    )
    print(f"time = {start_block_timestamp}; vault share price = {start_vault_share_price}")
    print(f"time = {lookback_timestamp}; vault share price = {lookback_vault_share_price}")
    print(f"Difference: {start_vault_share_price - lookback_vault_share_price=}")
    if start_vault_share_price < lookback_vault_share_price:
        print("WARNING: NEGATIVE INTEREST!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Check EZETH pool vault share price difference.")
    parser.add_argument(
        "--start-block",
        type=int,
        default=0,  # 0 will use current block.
        help="The starting block number.",
    )
    parser.add_argument(
        "--lookback",
        type=int,
        default=60 * 60 * 12,  # 12 hours
        help="The number of blocks to lookback from the starting block.",
    )
    args = parser.parse_args()
    main(args.start_block, args.lookback)
