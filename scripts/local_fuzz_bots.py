"""Runs random bots against a remote chain for fuzz testing."""

from __future__ import annotations

import argparse
import random
import sys
from typing import NamedTuple, Sequence

import numpy as np

from agent0 import LocalChain, LocalHyperdrive
from agent0.hyperfuzz.system_fuzz import generate_fuzz_hyperdrive_config, run_local_fuzz_bots
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar


def main(argv: Sequence[str] | None = None) -> None:
    """Runs local fuzz bots."""
    # TODO consolidate setup into single function

    parsed_args = parse_arguments(argv)

    log_to_rollbar = initialize_rollbar("localfuzzbots")

    rng_seed = random.randint(0, 10000000)
    rng = np.random.default_rng(rng_seed)

    # Set different ports if we're doing lp share price test
    if parsed_args.lp_share_price_test:
        chain_port = 11111
        db_port = 22222
    else:
        chain_port = 33333
        db_port = 44444

    local_chain_config = LocalChain.Config(chain_port=chain_port, db_port=db_port, block_timestamp_interval=12)

    while True:
        # Build interactive local hyperdrive
        # TODO can likely reuse some of these resources
        # instead, we start from scratch every time.
        chain = LocalChain(local_chain_config)

        # Fuzz over config values
        hyperdrive_config = generate_fuzz_hyperdrive_config(
            rng, log_to_rollbar, rng_seed, lp_share_price_test=parsed_args.lp_share_price_test
        )
        hyperdrive_pool = LocalHyperdrive(chain, hyperdrive_config)

        # TODO submit multiple transactions per block
        run_local_fuzz_bots(
            hyperdrive_pool,
            check_invariance=True,
            raise_error_on_failed_invariance_checks=False,
            raise_error_on_crash=False,
            log_to_rollbar=log_to_rollbar,
            run_async=False,
            random_advance_time=True,
            random_variable_rate=True,
            num_iterations=3000,
            lp_share_price_test=parsed_args.lp_share_price_test,
        )

        chain.cleanup()


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    lp_share_price_test: bool


def namespace_to_args(namespace: argparse.Namespace) -> Args:
    """Converts argprase.Namespace to Args.

    Arguments
    ---------
    namespace: argparse.Namespace
        Object for storing arg attributes.

    Returns
    -------
    Args
        Formatted arguments
    """
    return Args(
        lp_share_price_test=namespace.lp_share_price_test,
    )


def parse_arguments(argv: Sequence[str] | None = None) -> Args:
    """Parses input arguments.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.

    Returns
    -------
    Args
        Formatted arguments
    """
    parser = argparse.ArgumentParser(description="Runs a loop to check Hyperdrive invariants at each block.")
    parser.add_argument(
        "--lp-share-price-test",
        default=False,
        action="store_true",
        help="Runs the lp share price fuzz with specific fee and rate parameters.",
    )

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    main()
