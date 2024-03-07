"""Runs all fuzz tests forever."""

from __future__ import annotations

import argparse
import sys
from typing import NamedTuple, Sequence

from agent0.core.hyperdrive.interactive import ILocalChain
from agent0.core.interactive_fuzz import (
    fuzz_long_short_maturity_values,
    fuzz_path_independence,
    fuzz_present_value,
    fuzz_profit_check,
)
from agent0.core.interactive_fuzz.helpers import FuzzAssertionException
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar


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
    num_paths_checked = 20

    num_checks = 0
    while True:
        try:
            print("Running long short maturity test")
            chain_config = ILocalChain.Config(db_port=5434, chain_port=10001)
            long_maturity_vals_epsilon = 1e-14
            short_maturity_vals_epsilon = 1e-9
            fuzz_long_short_maturity_values(
                num_trades, long_maturity_vals_epsilon, short_maturity_vals_epsilon, chain_config
            )
        except FuzzAssertionException:
            pass
        # We catch other exceptions here, for some reason rollbar needs to be continuously running in order
        # to log.
        except Exception:  # pylint: disable=broad-except
            print("Unexpected error:", sys.exc_info()[0])

        try:
            print("Running path independence test")
            chain_config = ILocalChain.Config(db_port=5435, chain_port=10002)
            lp_share_price_epsilon = 1e-14
            effective_share_reserves_epsilon = 1e-4
            present_value_epsilon = 1e-4
            fuzz_path_independence(
                num_trades,
                num_paths_checked,
                lp_share_price_epsilon=lp_share_price_epsilon,
                effective_share_reserves_epsilon=effective_share_reserves_epsilon,
                present_value_epsilon=present_value_epsilon,
                chain_config=chain_config,
            )
        except FuzzAssertionException:
            pass
        # No need to catch other exceptions here, the test itself catches them

        try:
            print("Running fuzz profit test")
            chain_config = ILocalChain.Config(db_port=5436, chain_port=10003)
            fuzz_profit_check(chain_config)
        except FuzzAssertionException:
            pass
        except Exception:  # pylint: disable=broad-except
            print("Unexpected error:", sys.exc_info()[0])

        try:
            print("Running fuzz present value test")
            chain_config = ILocalChain.Config(db_port=5437, chain_port=10004)
            present_value_epsilon = 0.01
            fuzz_present_value(test_epsilon=present_value_epsilon, chain_config=chain_config)
        except FuzzAssertionException:
            pass
        except Exception:  # pylint: disable=broad-except
            print("Unexpected error:", sys.exc_info()[0])

        num_checks += 1
        if parsed_args.number_of_runs > 0 and num_checks >= parsed_args.number_of_runs:
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
