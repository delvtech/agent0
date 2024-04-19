"""Runs random bots against a remote chain for fuzz testing."""

from __future__ import annotations

import logging
import random

from fixedpointmath import FixedPoint

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
    local_chain_config = ILocalChain.Config(chain_port=11111, db_port=22222, block_timestamp_interval=12)
    chain = ILocalChain(local_chain_config)
    # TODO fuzz over pool configs
    rng_seed = random.randint(0, 10000000)
    hyperdrive_config = ILocalHyperdrive.Config(
        preview_before_trade=True,
        rng_seed=rng_seed,
        log_to_rollbar=log_to_rollbar,
        rollbar_log_prefix="localfuzzbots",
        crash_log_level=logging.CRITICAL,
        crash_report_additional_info={"rng_seed": rng_seed},
        # Initial hyperdrive config
        # TODO fuzz over these values, we set these to steth conditions for testing for now
        initial_liquidity=FixedPoint("50_000"),
        initial_fixed_apr=FixedPoint("0.035"),
        initial_time_stretch_apr=FixedPoint("0.035"),
        minimum_share_reserves=FixedPoint("0.001"),
        position_duration=60 * 60 * 24 * 7,  # 1 week
        checkpoint_duration=60 * 60,  # 1 hour
    )
    hyperdrive_pool = ILocalHyperdrive(chain, hyperdrive_config)

    hyperdrive_pool.run_dashboard()

    # TODO submit multiple transactions per block
    run_fuzz_bots(
        hyperdrive_pool,
        check_invariance=True,
        raise_error_on_failed_invariance_checks=True,
        raise_error_on_crash=False,
        log_to_rollbar=log_to_rollbar,
        run_async=False,
        random_advance_time=True,
        random_variable_rate=True,
    )


if __name__ == "__main__":
    main()
