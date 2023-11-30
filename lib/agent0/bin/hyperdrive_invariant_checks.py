"""Script for checking Hyperdrive invariants at each block."""
from __future__ import annotations

import argparse
import sys
import time
from typing import NamedTuple, Sequence

from ethpy import build_eth_config
from ethpy.hyperdrive.api import HyperdriveInterface
from fixedpointmath import FixedPoint


def main(argv: Sequence[str] | None = None) -> None:
    """Check Hyperdrive invariants each block.

    Arguments
    ---------
    argv: Sequence[str]
        A sequnce containing the uri to the database server and the test epsilon.
    """
    # Parse args
    parsed_args = parse_arguments(argv)
    eth_config = build_eth_config(parsed_args.eth_config_env_file)
    # Setup hyperdrive interface
    interface = HyperdriveInterface(eth_config)
    # Run the loop forever
    last_executed_block_number = 0
    while True:
        latest_block = interface.web3.eth.get_block("latest")
        latest_block_number = latest_block.get("number", None)
        if latest_block_number is None:
            raise AssertionError("Block has no number.")
        if latest_block_number > last_executed_block_number:
            # Get the variables to check
            pool_state = interface.get_hyperdrive_state(latest_block)
            share_reserves = pool_state.pool_info.share_reserves
            shorts_outstanding = pool_state.pool_info.shorts_outstanding
            withdraw_pool_proceeds = pool_state.pool_info.withdrawal_shares_proceeds
            minimum_share_reserves = pool_state.pool_config.minimum_share_reserves
            share_price = pool_state.pool_info.share_price
            global_exposure = pool_state.pool_info.long_exposure
            hyperdrive_balance = pool_state.hyperdrive_balance
            gov_fees_accrued = pool_state.gov_fees_accrued
            total_shares = pool_state.vault_shares
            epsilon = FixedPoint(scaled_value=parsed_args.test_epsilon)  # 10 wei

            # Check each invariant

            ### Total shares is correctly calculated
            assert (
                total_shares
                == share_reserves
                + shorts_outstanding / share_price
                + gov_fees_accrued
                + withdraw_pool_proceeds
                + epsilon
            ), f"{total_shares=} is incorrect."

            ### Longs and shorts should always be closed at maturity for the correct amounts
            # TODO: fail if any longs or shorts are at or past maturity
            # for each wallet:
            #   for each long:
            #     if long.maturity_time <= latest_checkpoint_time:
            #         assert long.is_closed()
            #   for each short:
            #       if short.maturity_time <= latest_checkpoint_time:
            #         assert short.is_closed()

            ### The system should always be solvent
            solvency = share_reserves - global_exposure - minimum_share_reserves
            assert solvency > 0, f"System is not solvent at block {latest_block_number}"

            ### The pool has more than the minimum share reserves
            assert (
                minimum_share_reserves <= share_reserves * share_price - global_exposure
            ), f"{minimum_share_reserves=} must be >= 0."

            ### The Hyperdrive base token balance is correct
            assert (
                hyperdrive_balance
                == share_reserves
                + shorts_outstanding / share_price
                + gov_fees_accrued
                + withdraw_pool_proceeds
                + epsilon
            ), f"{hyperdrive_balance=} is incorrect"

            ### Creating a checkpoint should never fail
            # TODO: This should already happen in the checkpoint bot?
            # interface.create_checkpoint(pool_state.block_number)

            # Update block number
            last_executed_block_number = latest_block_number
            time.sleep(parsed_args.sleep_time)


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    eth_config_env_file: str
    test_epsilon: int
    sleep_time: int


def namespace_to_args(namespace: argparse.Namespace) -> Args:
    """Converts argprase.Namespace to Args.

    Arguments
    ---------
    namespace: argparse.Namespace
        Object for storing arg attributes.

    Returns
    -------
    Args
    """
    return Args(
        eth_config_env_file=namespace.eth_config_env_file,
        test_epsilon=namespace.test_epsilon,
        sleep_time=namespace.sleep_time,
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
    """
    parser = argparse.ArgumentParser(description="Runs a loop to check Hyperdrive invariants at each block.")
    parser.add_argument(
        "--test_epsilon",
        type=int,
        default=10,
        help="The test epsilon amount, in WEI.",
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
