"""Runs random bots against a remote chain for fuzz testing."""

from __future__ import annotations

import logging
import random

from agent0 import ILocalChain, ILocalHyperdrive
from agent0.hyperfuzz.system_fuzz import run_fuzz_bots
from agent0.hyperlogs import setup_logging
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar


def main() -> None:
    """Runs local fuzz bots."""
    # TODO consolidate setup into single function

    log_to_rollbar = initialize_rollbar("localfuzzbots")
    setup_logging(
        log_stdout=True,
    )

    # Build interactive local hyperdrive
    # TODO explicitly use a block time here to allow for multiple transactions per block
    print("Launching local chain")
    local_chain_config = ILocalChain.Config(chain_port=11111, db_port=22222)
    chain = ILocalChain(local_chain_config)

    print("Launching hyperdrive")
    # TODO fuzz over pool configs
    rng_seed = random.randint(0, 10000000)
    hyperdrive_config = ILocalHyperdrive.Config(
        preview_before_trade=True,
        rng_seed=rng_seed,
        log_to_rollbar=log_to_rollbar,
        rollbar_log_prefix="localfuzzbots",
        crash_log_level=logging.CRITICAL,
        crash_report_additional_info={"rng_seed": rng_seed},
    )
    hyperdrive_pool = ILocalHyperdrive(chain, hyperdrive_config)

    print("Running fuzz bots")

    # TODO submit multiple transactions per block
    run_fuzz_bots(
        hyperdrive_pool,
        check_invariance=True,
        exit_on_failed_invariance_checks=True,
        exit_on_crash=False,
        log_to_rollbar=log_to_rollbar,
        run_async=False,
    )


if __name__ == "__main__":
    main()
