"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""

from __future__ import annotations

from agent0.chainsync.exec import data_analysis
from agent0.hyperlogs import setup_logging

if __name__ == "__main__":
    setup_logging(".logging/data_analysis.log", log_stdout=True)
    data_analysis(
        # This is the start block needed based on the devnet image, which corresponds
        # to the block that the contract was deployed.
        # TODO ideally would gather this from the deployer
        start_block=48,
    )
