"""Script for automatically detecting deployed pools using the registry contract on testnet,
and checking Hyperdrive invariants.

# Invariance checks (these should be True):
- hyperdrive base & eth balances are zero
- the expected total shares equals the hyperdrive balance in the vault contract
- the pool has more than the minimum share reserves
- the system is solvent, i.e. (share reserves - long exposure in shares - min share reserves) > 0
- if a hyperdrive trade happened then a checkpoint was created at the appropriate time
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
import time
from functools import partial
from typing import NamedTuple, Sequence

from agent0 import Chain, Hyperdrive
from agent0.ethpy.hyperdrive import get_hyperdrive_registry_from_artifacts
from agent0.hyperfuzz.system_fuzz.invariant_checks import run_invariant_checks
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar, log_rollbar_exception, log_rollbar_message
from agent0.utils import async_runner

LOOKBACK_BLOCK_LIMIT = 1000


def main(argv: Sequence[str] | None = None) -> None:
    """Check Hyperdrive invariants each block.

    Arguments
    ---------
    argv: Sequence[str]
        A sequence containing the uri to the database server.
    """
    # pylint: disable=too-many-locals

    parsed_args = parse_arguments(argv)

    if parsed_args.infra:
        # TODO Abstract this method out for infra scripts
        # Get the rpc uri from env variable
        rpc_uri = os.getenv("RPC_URI", None)
        if rpc_uri is None:
            raise ValueError("RPC_URI is not set")

        chain = Chain(rpc_uri, Chain.Config(use_existing_postgres=True))

        # Get the registry address from artifacts
        registry_address = os.getenv("REGISTRY_ADDRESS", None)
        if registry_address is None or registry_address == "":
            artifacts_uri = os.getenv("ARTIFACTS_URI", None)
            if artifacts_uri is None:
                raise ValueError("ARTIFACTS_URI must be set if registry address is not set.")
            registry_address = get_hyperdrive_registry_from_artifacts(artifacts_uri)
    else:
        chain = Chain(parsed_args.rpc_uri)
        registry_address = parsed_args.registry_addr

    rollbar_environment_name = "invariant_checks"
    log_to_rollbar = initialize_rollbar(rollbar_environment_name)

    # Keeps track of the last time we checked for a new pool
    last_pool_check_block_number = 0
    # Keeps track of the last time we executed an invariant check
    batch_check_start_block = chain.block_number()

    # Run the loop forever
    while True:
        # The batch_check_end_block is inclusive
        # (i.e., we do batch_check_end_block + 1 in the loop range)
        batch_check_end_block = chain.block_number()

        # Check if we need to check for new pools
        if batch_check_end_block > last_pool_check_block_number + parsed_args.pool_check_sleep_blocks:
            logging.info("Checking for new pools...")
            deployed_pools = Hyperdrive.get_hyperdrive_pools_from_registry(chain, registry_address)
            last_pool_check_block_number = batch_check_end_block

        # If a block hasn't ticked, we sleep
        if batch_check_start_block > batch_check_end_block:
            # take a nap
            time.sleep(1)
            continue

        # Look at the number of blocks we need to iterate through
        # If it's past the limit, log an error and catch up by
        # skipping to the latest block
        if (batch_check_end_block - batch_check_start_block) > LOOKBACK_BLOCK_LIMIT:
            error_message = "Unable to keep up with invariant checks. Skipping check blocks."
            logging.error(error_message)
            log_rollbar_message(error_message, logging.ERROR)
            batch_check_start_block = batch_check_end_block

        # Loop through all deployed pools and run invariant checks
        print(f"Running invariant checks from block {batch_check_start_block} to {batch_check_end_block} (inclusive)")
        for check_block in range(batch_check_start_block, batch_check_end_block + 1):
            check_block_data = chain.block_data(block_identifier=check_block)
            partials = [
                partial(
                    run_invariant_checks,
                    check_block_data=check_block_data,
                    interface=hyperdrive_obj.interface,
                    log_to_rollbar=log_to_rollbar,
                    pool_name=hyperdrive_obj.name,
                )
                for hyperdrive_obj in deployed_pools
            ]

            logging.info(
                "Running invariant checks for block %s on pools %s", check_block, [pool.name for pool in deployed_pools]
            )
            asyncio.run(async_runner(return_exceptions=False, funcs=partials))

        batch_check_start_block = batch_check_end_block + 1


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    pool_check_sleep_blocks: int
    infra: bool
    registry_addr: str
    rpc_uri: str


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

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    # Wrap everything in a try catch to log any non-caught critical errors and log to rollbar
    try:
        main()
    except Exception as e:  # pylint: disable=broad-except
        log_rollbar_exception(e, logging.CRITICAL, rollbar_log_prefix="Uncaught critical error in invariant checks.")
        raise e
