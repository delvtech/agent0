"""Runs random bots against a remote chain for fuzz testing."""

from __future__ import annotations

import random

import numpy as np

from agent0 import LocalChain, LocalHyperdrive
from agent0.hyperfuzz.system_fuzz import generate_fuzz_hyperdrive_config, run_fuzz_bots
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar


def main() -> None:
    """Runs local fuzz bots."""
    # TODO consolidate setup into single function

    log_to_rollbar = initialize_rollbar("localfuzzbots")

    rng_seed = random.randint(0, 10000000)
    rng = np.random.default_rng(rng_seed)

    local_chain_config = LocalChain.Config(chain_port=11111, db_port=22222, block_timestamp_interval=12)

    while True:
        # Build interactive local hyperdrive
        # TODO can likely reuse some of these resources
        # instead, we start from scratch every time.
        chain = LocalChain(local_chain_config)

        # Fuzz over config values
        hyperdrive_config = generate_fuzz_hyperdrive_config(rng, log_to_rollbar, rng_seed)
        hyperdrive_pool = LocalHyperdrive(chain, hyperdrive_config)

        # TODO submit multiple transactions per block
        run_fuzz_bots(
            hyperdrive_pool,
            check_invariance=True,
            raise_error_on_failed_invariance_checks=False,
            raise_error_on_crash=False,
            log_to_rollbar=log_to_rollbar,
            run_async=False,
            random_advance_time=True,
            random_variable_rate=True,
            num_iterations=3000,
        )

        chain.cleanup()


if __name__ == "__main__":
    main()
