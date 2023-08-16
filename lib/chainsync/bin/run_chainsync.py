"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

from chainsync.exec import acquire_data
from elfpy.utils import logs as log_utils

if __name__ == "__main__":
    # setup constants
    START_BLOCK = 0
    # Look back limit for backfilling
    LOOKBACK_BLOCK_LIMIT = 100000

    log_utils.setup_logging(".logging/acquire_data.log", log_stdout=True)
    acquire_data(
        START_BLOCK,
        LOOKBACK_BLOCK_LIMIT,
    )
