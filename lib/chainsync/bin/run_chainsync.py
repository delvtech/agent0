"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

from chainsync.exec import acquire_data
from elfpy.utils import logs as log_utils
from ethpy import build_eth_config

if __name__ == "__main__":
    # setup constants
    START_BLOCK = 0
    # Look back limit for backfilling
    LOOKBACK_BLOCK_LIMIT = 100000

    # Load parameters from env vars if they exist
    config = build_eth_config()

    log_utils.setup_logging(".logging/acquire_data.log", log_stdout=True)
    acquire_data(
        config.ARTIFACTS_URL,
        config.RPC_URL,
        config.ABI_DIR,
        START_BLOCK,
        LOOKBACK_BLOCK_LIMIT,
    )
