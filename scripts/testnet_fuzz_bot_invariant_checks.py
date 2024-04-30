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
import sys
import time
from typing import NamedTuple, Sequence

from agent0 import Chain, Hyperdrive
from agent0.hyperfuzz.system_fuzz.invariant_checks import run_invariant_checks
from agent0.hyperlogs import setup_logging
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar


def main(argv: Sequence[str] | None = None) -> None:
    """Check Hyperdrive invariants each block.

    Arguments
    ---------
    argv: Sequence[str]
        A sequence containing the uri to the database server and the test epsilon.
    """

    parsed_args = parse_arguments(argv)
    chain = Chain(parsed_args.rpc_uri)

    # We use the logical name if we don't specify pool addr, otherwise we use the pool addr
    rollbar_environment_name = "testnet_fuzz_bot_invariant_check"
    log_to_rollbar = initialize_rollbar(rollbar_environment_name)
    setup_logging(
        log_stdout=True,
    )

    # We calculate how many blocks we should wait before checking for a new pool
    pool_check_num_blocks = parsed_args.pool_check_sleep_time // 12

    last_executed_block_number = -pool_check_num_blocks - 1  # no matter what we will run the check the first time
    last_pool_check_block_number = 0

    hyperdrive_objs: dict[str, Hyperdrive] = {}

    # Run the loop forever
    while True:
        # Check for new pools
        latest_block = chain.curr_block_data()
        latest_block_number = latest_block.get("number", None)
        if latest_block_number is None:
            raise AssertionError("Block has no number.")

        if latest_block_number > last_pool_check_block_number + pool_check_num_blocks:
            logging.info("Checking for new pools...")
            # Reset hyperdrive objs
            hyperdrive_objs: dict[str, Hyperdrive] = {}
            # First iteration, get list of deployed pools
            deployed_pools = Hyperdrive.get_hyperdrive_addresses_from_registry(parsed_args.registry_addr, chain)
            for name, addr in deployed_pools.items():
                logging.info("Adding pool %s", name)
                hyperdrive_objs[name] = Hyperdrive(chain, addr)
            last_pool_check_block_number = latest_block_number

        if not latest_block_number > last_executed_block_number:
            # take a nap
            time.sleep(parsed_args.invariance_check_sleep_time)
            continue

        # Update block number
        last_executed_block_number = latest_block_number
        # Loop through all deployed pools and run invariant checks
        for name, hyperdrive_obj in hyperdrive_objs.items():
            logging.info("Running invariance check on %s", name)
            run_invariant_checks(
                latest_block=latest_block,
                interface=hyperdrive_obj.interface,
                test_epsilon=parsed_args.test_epsilon,
                raise_error_on_failure=False,
                log_to_rollbar=log_to_rollbar,
                pool_name=name,
            )


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    test_epsilon: float
    invariance_check_sleep_time: int
    pool_check_sleep_time: int
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
        test_epsilon=namespace.test_epsilon,
        invariance_check_sleep_time=namespace.invariance_check_sleep_time,
        pool_check_sleep_time=namespace.pool_check_sleep_time,
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
        "--test-epsilon",
        type=float,
        default=1e-4,
        help="The allowed error for equality tests.",
    )
    parser.add_argument(
        "--invariance-check-sleep-time",
        type=int,
        default=5,
        help="Sleep time between invariance checks, in seconds.",
    )
    parser.add_argument(
        "--pool-check-sleep-time",
        type=int,
        default=3600,  # 1 hour
        help="Sleep time between checking for new pools, in seconds.",
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
    main()
