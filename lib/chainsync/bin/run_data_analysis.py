"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""
from __future__ import annotations

from chainsync.exec import data_analysis
from hyperlogs import setup_logging

if __name__ == "__main__":
    setup_logging(".logging/data_analysis.log", log_stdout=True)
    data_analysis()
