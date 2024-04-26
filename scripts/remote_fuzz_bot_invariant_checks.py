"""Script for checking Hyperdrive invariants at each block on a remote chain.
"""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import NamedTuple, Sequence

from web3 import Web3

from agent0 import IHyperdrive
from agent0.core.base.config import EnvironmentConfig
from agent0.ethpy import build_eth_config
from agent0.ethpy.hyperdrive import HyperdriveReadInterface
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

    # Setup the experiment
    parsed_args, interface = setup_fuzz(argv)

    # We use the logical name if we don't specify pool addr, otherwise we use the pool addr
    if parsed_args.pool_addr == "":
        rollbar_environment_name = "remote_fuzz_bot_invariant_check_" + parsed_args.pool
    else:
        rollbar_environment_name = "remote_fuzz_bot_invariant_check_" + parsed_args.pool_addr

    log_to_rollbar = initialize_rollbar(rollbar_environment_name)

    # Run the loop forever
    last_executed_block_number = 0  # no matter what we will run the check the first time
    while True:
        latest_block = interface.get_block("latest")
        latest_block_number = latest_block.get("number", None)
        if latest_block_number is None:
            raise AssertionError("Block has no number.")
        if not latest_block_number > last_executed_block_number:
            # take a nap
            time.sleep(parsed_args.sleep_time)
            continue
        # Update block number
        last_executed_block_number = latest_block_number
        run_invariant_checks(
            latest_block=latest_block,
            interface=interface,
            test_epsilon=parsed_args.test_epsilon,
            raise_error_on_failure=False,
            log_to_rollbar=log_to_rollbar,
        )


# TODO consolidate setup fuzz within hyperfuzz
def setup_fuzz(argv: Sequence[str] | None) -> tuple[Args, HyperdriveReadInterface]:
    """Setup the fuzz config & interface.

    Arguments
    ---------
    argv: Sequence[str]
        A sequnce containing the uri to the database server and the test epsilon.

    Returns
    -------
    tuple[Args, HyperdriveReadInterface]
        The parsed arguments and interface constructed from those arguments.
    """
    parsed_args = parse_arguments(argv)

    eth_config = build_eth_config(parsed_args.eth_config_env_file)
    # CLI arguments overwrite what's in the env file
    if parsed_args.rpc_uri != "":
        eth_config.rpc_uri = parsed_args.rpc_uri

    env_config = EnvironmentConfig(
        delete_previous_logs=False,
        halt_on_errors=False,
        log_filename=".logging/invariant_checks.log",
        log_level=logging.ERROR,
        log_stdout=False,
        global_random_seed=1234,
        username="INVARIANT_CHECKS",
    )
    # Setup logging
    setup_logging(
        log_filename=env_config.log_filename,
        max_bytes=env_config.max_bytes,
        log_level=env_config.log_level,
        delete_previous_logs=env_config.delete_previous_logs,
        log_stdout=env_config.log_stdout,
        log_format_string=env_config.log_formatter,
    )

    # Setup hyperdrive interface
    if parsed_args.pool_addr == "":
        hyperdrive_addresses = IHyperdrive.get_hyperdrive_addresses_from_artifacts(eth_config.artifacts_uri)
        if parsed_args.pool not in hyperdrive_addresses:
            raise ValueError(
                f"Pool {parsed_args.pool} not recognized. Available options are {list(hyperdrive_addresses.keys())}"
            )
        hyperdrive_address = hyperdrive_addresses[parsed_args.pool]
    else:
        hyperdrive_address = Web3.to_checksum_address(parsed_args.pool_addr)

    interface = HyperdriveReadInterface(eth_config, hyperdrive_address=hyperdrive_address)
    return parsed_args, interface


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    test_epsilon: float
    eth_config_env_file: str
    sleep_time: int
    pool: str
    pool_addr: str
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
        eth_config_env_file=namespace.eth_config_env_file,
        sleep_time=namespace.sleep_time,
        pool=namespace.pool,
        pool_addr=namespace.pool_addr,
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
        "--test_epsilon",
        type=float,
        default=1e-4,
        help="The allowed error for equality tests.",
    )
    parser.add_argument(
        "--eth_config_env_file",
        type=str,
        default="eth.env",
        help="String pointing to eth config env file.",
    )
    parser.add_argument(
        "--sleep_time",
        type=int,
        default=5,
        help="Sleep time between checks, in seconds.",
    )

    parser.add_argument(
        "--pool",
        type=str,
        default="erc4626_hyperdrive",
        help='The logical name of the pool to connect to. Options are "erc4626_hyperdrive" and "stethhyperdrive".',
    )

    parser.add_argument(
        "--pool-addr",
        type=str,
        default="",
        help="The address of the hyperdrive pool to connect to. Uses `--pool` if not provided.",
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
