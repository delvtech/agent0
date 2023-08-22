"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

from chainsync.exec import data_analysis
from elfpy.utils import logs as log_utils

if __name__ == "__main__":
    log_utils.setup_logging(".logging/data_analysis.log", log_stdout=True)
    data_analysis()
