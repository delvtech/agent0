import argparse
import os

from dotenv import load_dotenv

from agent0 import Chain, Hyperdrive

load_dotenv(".env")
DEV_RPC_URI = os.getenv("DEV_RPC_URI", "")
ALCHEMY_KEY = os.getenv("ALCHEMY_KEY", "")
RPC_URI = DEV_RPC_URI + ALCHEMY_KEY
REGISTRY_ADDRESS = os.getenv("REGISTRY_ADDRESS", "")


def main(start_blocktime: int, lookback_length: int):
    fork_block_number: int | None = None
    with Chain(RPC_URI) as chain:
        # If the start block is zero, use the current block
        if start_blocktime <= 0:
          start_blocktime = chain.block_time()
          start_block = chain.block_number()
        # Otherwise, find the block with the given blocktime
        else:


        



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
