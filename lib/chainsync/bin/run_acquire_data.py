"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

from chainsync.exec import acquire_data
from elfpy.utils import logs as log_utils

if __name__ == "__main__":
    log_utils.setup_logging(".logging/acquire_data.log", log_stdout=True)
    acquire_data()
