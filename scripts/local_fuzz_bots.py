"""Runs random bots against a remote chain for fuzz testing."""

from __future__ import annotations

import argparse
import logging
import random
import sys
import time
from typing import NamedTuple, Sequence

import numpy as np

from agent0 import LocalChain, LocalHyperdrive
from agent0.hyperfuzz import FuzzAssertionException
from agent0.hyperfuzz.system_fuzz import generate_fuzz_hyperdrive_config, run_local_fuzz_bots
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar


def main(argv: Sequence[str] | None = None) -> None:
    """Runs local fuzz bots.

    Arguments
    ---------
    argv: Sequence[str]
        A sequence containing the uri to the database server and the test epsilon.
    """
    # TODO consolidate setup into single function

    parsed_args = parse_arguments(argv)

    log_to_rollbar = initialize_rollbar("localfuzzbots")

    rng_seed = random.randint(0, 10000000)
    rng = np.random.default_rng(rng_seed)

    # Negative chain port means default
    if parsed_args.chain_port < 0:
        if parsed_args.lp_share_price_test:
            chain_port = 11111
        else:
            chain_port = 33333
    else:
        chain_port = parsed_args.chain_port

    # Set different ports if we're doing lp share price test
    if parsed_args.lp_share_price_test:
        db_port = 22222
    else:
        db_port = 44444

    local_chain_config = LocalChain.Config(
        chain_port=chain_port,
        db_port=db_port,
        block_timestamp_interval=12,
        log_level=logging.WARNING,
        preview_before_trade=True,
        log_to_rollbar=log_to_rollbar,
        rollbar_log_prefix="localfuzzbots",
        rng=rng,
        crash_log_level=logging.CRITICAL,
        crash_report_additional_info={"rng_seed": rng_seed},
        gas_limit=int(1e6),  # Plenty of gas limit for transactions
    )

    while True:
        # Build interactive local hyperdrive
        # TODO can likely reuse some of these resources
        # instead, we start from scratch every time.
        chain = LocalChain(local_chain_config)

        # Fuzz over config values
        hyperdrive_config = generate_fuzz_hyperdrive_config(rng, lp_share_price_test=parsed_args.lp_share_price_test)
        hyperdrive_pool = LocalHyperdrive(chain, hyperdrive_config)

        raise_error_on_fail = False
        if parsed_args.pause_on_invariance_fail:
            raise_error_on_fail = True

        # TODO submit multiple transactions per block
        try:
            run_local_fuzz_bots(
                hyperdrive_pool,
                check_invariance=True,
                raise_error_on_failed_invariance_checks=raise_error_on_fail,
                raise_error_on_crash=False,
                log_to_rollbar=log_to_rollbar,
                run_async=False,
                random_advance_time=True,
                random_variable_rate=True,
                num_iterations=3000,
                lp_share_price_test=parsed_args.lp_share_price_test,
            )

        except FuzzAssertionException as e:
            logging.error("Pausing pool on fuzz assertion exception %s", repr(e))
            while True:
                time.sleep(1000000)

        chain.cleanup()


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    lp_share_price_test: bool
    pause_on_invariance_fail: bool
    chain_port: int


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
        pause_on_invariance_fail=namespace.pause_on_invariance_fail,
        chain_port=namespace.chain_port,
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
    parser.add_argument(
        "--pause-on-invariance-fail",
        default=False,
        action="store_true",
        help="Pause execution on invariance failure.",
    )
    parser.add_argument(
        "--chain_port",
        type=int,
        default=-1,
        help="The port to run anvil on.",
    )

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    main()
