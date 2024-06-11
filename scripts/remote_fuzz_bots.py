"""Runs random bots against a remote chain."""

from __future__ import annotations

import argparse
import logging
import os
import random
import sys
from typing import NamedTuple, Sequence

import numpy as np

from agent0 import Chain, Hyperdrive
from agent0.ethpy.hyperdrive import get_hyperdrive_registry_from_artifacts
from agent0.hyperfuzz.system_fuzz import run_fuzz_bots
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar


def main(argv: Sequence[str] | None = None) -> None:
    """Runs local fuzz bots.

    Arguments
    ---------
    argv: Sequence[str]
        A sequence containing the uri to the database server.
    """
    # TODO consolidate setup into single function and clean up.
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-locals

    parsed_args = parse_arguments(argv)

    if parsed_args.infra:
        # Get the rpc uri from env variable
        rpc_uri = os.getenv("RPC_URI", None)
        if rpc_uri is None:
            raise ValueError("RPC_URI is not set")
        use_existing_postgres = True
        # Get the registry address from artifacts
        artifacts_uri = os.getenv("ARTIFACTS_URI", None)
        if artifacts_uri is None:
            raise ValueError("ARTIFACTS_URI is not set")
        registry_address = get_hyperdrive_registry_from_artifacts(artifacts_uri)
    else:
        rpc_uri = parsed_args.rpc_uri
        use_existing_postgres = False
        registry_address = parsed_args.registry_addr

    log_to_rollbar = initialize_rollbar("remotefuzzbots")

    # Negative rng_seed means default
    if parsed_args.rng_seed < 0:
        rng_seed = random.randint(0, 10000000)
    else:
        rng_seed = parsed_args.rng_seed
    rng = np.random.default_rng(rng_seed)

    chain_config = Chain.Config(
        use_existing_postgres=use_existing_postgres,
        log_level=logging.WARNING,
        preview_before_trade=True,
        log_to_rollbar=log_to_rollbar,
        rollbar_log_prefix="remotefuzzbots",
        rng=rng,
        crash_log_level=logging.CRITICAL,
        crash_report_additional_info={"rng_seed": rng_seed},
        gas_limit=int(1e6),  # Plenty of gas limit for transactions
    )
    # Build interactive local hyperdrive
    # TODO can likely reuse some of these resources
    # instead, we start from scratch every time.
    chain = Chain(rpc_uri=rpc_uri, config=chain_config)

    last_pool_check_block_number = 0
    # Get list of deployed pools on initial iteration
    deployed_pools = Hyperdrive.get_hyperdrive_pools_from_registry(chain, registry_address)

    while True:
        # Check for new pools
        latest_block = chain.block_data()
        latest_block_number = latest_block.get("number", None)
        if latest_block_number is None:
            raise AssertionError("Block has no number.")

        if latest_block_number > last_pool_check_block_number + parsed_args.pool_check_sleep_blocks:
            logging.info("Checking for new pools...")
            # First iteration, get list of deployed pools
            deployed_pools = Hyperdrive.get_hyperdrive_pools_from_registry(chain, registry_address)
            last_pool_check_block_number = latest_block_number

        run_fuzz_bots(
            chain,
            hyperdrive_pools=deployed_pools,
            check_invariance=False,  # We don't check invariance here
            raise_error_on_failed_invariance_checks=False,
            raise_error_on_crash=False,
            log_to_rollbar=log_to_rollbar,
            ignore_raise_error_func=None,
            run_async=False,
            random_advance_time=False,
            random_variable_rate=False,
            num_iterations=parsed_args.pool_check_sleep_blocks,
            lp_share_price_test=False,
        )

        chain.cleanup()


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    pool_check_sleep_blocks: int
    infra: bool
    registry_addr: str
    rpc_uri: str
    rng_seed: int


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
        pool_check_sleep_blocks=namespace.pool_check_sleep_blocks,
        infra=namespace.infra,
        registry_addr=namespace.registry_addr,
        rpc_uri=namespace.rpc_uri,
        rng_seed=namespace.rng_seed,
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
        "--pool-check-sleep-blocks",
        type=int,
        default=300,  # 1 hour for 12 second block time
        help="Number of blocks in between checking for new pools.",
    )

    parser.add_argument(
        "--infra",
        default=False,
        action="store_true",
        help="Infra mode, we get registry address from artifacts, and we fund a random account with eth as sender.",
    )

    parser.add_argument(
        "--registry-addr",
        type=str,
        default="",
        help="The address of the registry.",
    )
    parser.add_argument(
        "--rpc-uri",
        type=str,
        default="",
        help="The RPC URI of the chain.",
    )
    parser.add_argument(
        "--rng-seed",
        type=int,
        default=-1,
        help="The random seed to use for the fuzz run.",
    )

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    main()
