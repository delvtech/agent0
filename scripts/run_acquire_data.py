"""Script to format on-chain hyperdrive pool, config, and transaction data post-processing."""

from __future__ import annotations

import os

from agent0.chainsync.exec import acquire_data
from agent0.ethpy.hyperdrive.addresses import get_hyperdrive_addresses_from_artifacts
from agent0.hyperlogs import setup_logging

if __name__ == "__main__":
    setup_logging(".logging/acquire_data.log", log_stdout=True)
    # Get the RPC URI and pool address from environment var
    rpc_uri = os.getenv("RPC_URI", "http://localhost:8545")
    # TODO get this from the registry after refactor
    artifacts_uri = os.getenv("ARTIFACTS_URI", "http://localhost:8080")
    hyperdrive_addr = get_hyperdrive_addresses_from_artifacts(artifacts_uri)["erc4626_hyperdrive"]
    acquire_data(
        # This is the start block needed based on the devnet image, which corresponds
        # to the block that the contract was deployed.
        # TODO ideally would gather this from the deployer
        start_block=48,
        rpc_uri=rpc_uri,
        hyperdrive_addresses=[hyperdrive_addr],
    )
