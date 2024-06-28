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
import logging
import os
import sys
import time
from typing import NamedTuple, Sequence

from agent0 import Chain, Hyperdrive
from agent0.ethpy.hyperdrive import get_hyperdrive_registry_from_artifacts
from agent0.hyperfuzz.system_fuzz.invariant_checks import run_invariant_checks
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar, log_rollbar_exception


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

    # We calculate how many blocks we should wait before checking for a new pool
    last_executed_block_number = (
        -parsed_args.pool_check_sleep_blocks - 1
    )  # no matter what we will run the check the first time
    last_pool_check_block_number = 0
    # Get deployed pools on first iteration
    deployed_pools = Hyperdrive.get_hyperdrive_pools_from_registry(chain, registry_address)

    # Run the loop forever
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

        # TODO ensure we check on every block, and wait for a new mined block
        # Throw a critical if it gets behind
        if not latest_block_number > last_executed_block_number:
            # take a nap
            time.sleep(parsed_args.invariance_check_sleep_time)
            continue

        # Update block number
        last_executed_block_number = latest_block_number
        # Loop through all deployed pools and run invariant checks
        for hyperdrive_obj in deployed_pools:
            name = hyperdrive_obj.name
            logging.info("Running invariance check on %s", name)
            # This returns the list of all exceptions for failed checks,
            # we ignore them here since we don't want to stop the script,
            # we just log them.
            _ = run_invariant_checks(
                latest_block=latest_block,
                interface=hyperdrive_obj.interface,
                log_to_rollbar=log_to_rollbar,
                pool_name=name,
            )


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    invariance_check_sleep_time: int
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
        invariance_check_sleep_time=namespace.invariance_check_sleep_time,
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
        "--invariance-check-sleep-time",
        type=int,
        default=5,
        help="Sleep time between invariance checks, in seconds.",
    )

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
