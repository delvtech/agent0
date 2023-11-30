"""Script for checking Hyperdrive invariants at each block."""
from __future__ import annotations

import argparse
import sys
from typing import NamedTuple, Sequence

from ethpy import build_eth_config
from ethpy.base import initialize_web3_with_http_provider
from ethpy.hyperdrive.api import HyperdriveInterface


def main(argv: Sequence[str] | None = None) -> None:
    """Check Hyperdrive invariants each block.

    Arguments
    ---------
    database_api_uri: str
        The uri to the database server.
    """
    # Parse args
    eth_config_env_file = parse_arguments(argv)
    eth_config = build_eth_config()
    # Setup hyperdrive interface
    web3 = initialize_web3_with_http_provider(rpc_uri, reset_provider=False)
    hyperdrive = HyperdriveInterface(
        eth_config, contract_addresses, read_retry_count=read_retry_count, write_retry_count=write_retry_count
    )
    # Run the loop
    last_executed_block = 0
    while True:
        latest_block = web3.eth.get_block("latest")
        latest_block_number = latest_block.get("number", None)
        if latest_block_number is None:
            raise AssertionError("Block has no number.")
        if latest_block_number > last_executed_block:
            # Get the pool state
            pool_state = interface.get_current_state(latst_block_number)
            # Check each invariant
            #   total shares == share reserves + shorts outstanding/c + _governanceFeesAccrued + _withdrawalPool.proceeds + epsilon
            #   the system should always be solvent (solvency = share_reserves - global_exposure - minimum_share_reserves > 0)
            #   longs and shorts should always be closed at maturity for the correct amounts
            #   share reserves * c - long exposure >= minimum share reserves
            #   balanceOf(hyperdrive) == share reserves + shorts outstanding/c + _governanceFeesAccrued + _withdrawalPool.proceeds + epsilon
            #   creating a checkpoint should never fail
            last_executed_block = latest_block_number


class Args(NamedTuple):
    """Command line arguments for pypechain."""

    eth_config_env_file: str


def namespace_to_args(namespace: argparse.Namespace) -> Args:
    """Converts argprase.Namespace to Args."""
    return Args(
        eth_config_env_file=namespace.eth_config_env_file,
    )


def parse_arguments(argv: Sequence[str] | None = None) -> Args:
    """Parses input arguments"""
    parser = argparse.ArgumentParser(description="Runs a loop to check Hyperdrive invariants at each block.")
    parser.add_argument(
        "--eth_config_env_file",
        type=str,
        default="eth.env",
        help="String pointing to eth config env file.",
    )

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    # If no arguments were passed, display the help message and exit
    if len(argv) == 1:
        parser.print_help(sys.stderr)
        sys.exit(1)

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    main()
