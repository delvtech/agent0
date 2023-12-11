"""Runs all fuzz tests forever."""
from __future__ import annotations

import argparse
import sys
from typing import NamedTuple, Sequence

from hyperlogs.rollbar_utilities import initialize_rollbar

from agent0.hyperdrive.interactive.chain import LocalChain
from agent0.interactive_fuzz import (
    fuzz_hyperdrive_balance,
    fuzz_long_short_maturity_values,
    fuzz_path_independence,
    fuzz_profit_check,
)
from agent0.interactive_fuzz.helpers import FuzzAssertionException


def main(argv: Sequence[str] | None = None):
    """Runs all fuzz tests.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    parsed_args = parse_arguments(argv)

    initialize_rollbar("interactivefuzz")

    num_trades = 10
    num_paths_checked = 10

    num_checks = 0
    while True:
        try:
            print("Running hyperdrive balance test")
            chain_config = LocalChain.Config(db_port=5433, chain_port=10000)
            fuzz_hyperdrive_balance(num_trades, chain_config)
        except FuzzAssertionException:
            pass

        try:
            print("Running long short maturity test")
            chain_config = LocalChain.Config(db_port=5434, chain_port=10001)
            fuzz_long_short_maturity_values(num_trades, chain_config)
        except FuzzAssertionException:
            pass

        try:
            print("Running path independence test")
            chain_config = LocalChain.Config(db_port=5435, chain_port=10002)
            fuzz_path_independence(num_trades, num_paths_checked, chain_config)
        except FuzzAssertionException:
            pass

        try:
            print("Running fuzz profit test")
            chain_config = LocalChain.Config(db_port=5436, chain_port=10003)
            fuzz_profit_check(chain_config)
        except FuzzAssertionException:
            pass
        num_checks += 1
        if parsed_args.number_of_runs > 0 and num_checks > parsed_args.number_of_runs:
            break


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    number_of_runs: int


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
        number_of_runs=namespace.number_of_runs,
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
        "--number_of_runs",
        type=int,
        default=0,
        help="The number times to run the tests. If not set, will run forever.",
    )
    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    main()
