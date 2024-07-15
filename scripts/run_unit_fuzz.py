"""Runs all unit fuzz tests forever."""

from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import NamedTuple, Sequence

import rollbar

from agent0.core.hyperdrive.interactive import LocalChain
from agent0.hyperfuzz import FuzzAssertionException
from agent0.hyperfuzz.unit_fuzz import (
    fuzz_long_short_maturity_values,
    fuzz_path_independence,
    fuzz_present_value,
    fuzz_profit_check,
)
from agent0.hyperlogs.rollbar_utilities import initialize_rollbar

# pylint: disable=too-many-statements
# pylint: disable=too-many-branches


def main(argv: Sequence[str] | None = None):
    """Runs all fuzz tests.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    parsed_args = parse_arguments(argv)

    if parsed_args.steth:
        _ = initialize_rollbar("steth_unitfuzz")
    else:
        _ = initialize_rollbar("erc4626_unitfuzz")

    num_trades = 10
    num_paths_checked = 20

    # Empty string means default
    if parsed_args.chain_host == "":
        chain_host = None
    else:
        chain_host = parsed_args.chain_host

    # Negative port means default
    if parsed_args.chain_port < 0:
        if parsed_args.steth:
            chain_port = 10001
        else:
            chain_port = 11001
    else:
        chain_port = parsed_args.chain_port

    if parsed_args.steth:
        db_port = 5434
    else:
        db_port = 6434

    num_checks = 0
    while True:
        try:
            print("Running long short maturity test")
            chain_config = LocalChain.Config(
                db_port=db_port,
                chain_host=chain_host,
                chain_port=chain_port,
                log_filename=".logging/fuzz_long_short_maturity_values.log",
                log_to_stdout=False,
                gas_limit=int(1e6),  # Plenty of gas limit for transactions
                # Try 5 times when creating checkpoints for advancing time transactions
                advance_time_create_checkpoint_retry_count=5,
            )
            long_maturity_vals_epsilon = 1e-17
            short_maturity_vals_epsilon = 1e-9
            fuzz_long_short_maturity_values(
                num_trades,
                long_maturity_vals_epsilon,
                short_maturity_vals_epsilon,
                chain_config,
                parsed_args.steth,
                pause_on_fail=parsed_args.pause_on_fail,
            )
        except FuzzAssertionException:
            pass
        except Exception as e:  # pylint: disable=broad-except
            print("Unexpected error:\n", repr(e))
            rollbar.report_exc_info(level="critical")
            if parsed_args.pause_on_fail:
                # We don't log info from logging, so we print to ensure this shows up
                # TODO we don't have access to the hyperdrive pool here, ideally we would
                # report it here
                print(f"Pausing pool (port:{chain_port}) crash {repr(e)}")
                while True:
                    time.sleep(1000000)

        time.sleep(1)

        try:
            print("Running path independence test")
            chain_config = LocalChain.Config(
                db_port=db_port,
                chain_host=chain_host,
                chain_port=chain_port,
                log_filename=".logging/fuzz_path_independence.log",
                log_to_stdout=False,
                gas_limit=int(1e6),  # Plenty of gas limit for transactions
                # Try 5 times when creating checkpoints for advancing time transactions
                advance_time_create_checkpoint_retry_count=5,
            )
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
                steth=parsed_args.steth,
                pause_on_fail=parsed_args.pause_on_fail,
            )
        except FuzzAssertionException:
            pass
        except Exception as e:  # pylint: disable=broad-except
            print("Unexpected error:\n", repr(e))
            rollbar.report_exc_info(level="critical")
            if parsed_args.pause_on_fail:
                # We don't log info from logging, so we print to ensure this shows up
                # TODO we don't have access to the hyperdrive pool here, ideally we would
                # report it here
                print(f"Pausing pool (port:{chain_port}) crash {repr(e)}")
                while True:
                    time.sleep(1000000)

        time.sleep(1)

        try:
            print("Running fuzz profit test")
            chain_config = LocalChain.Config(
                db_port=db_port,
                chain_host=chain_host,
                chain_port=chain_port,
                log_filename=".logging/fuzz_profit_check.log",
                log_to_stdout=False,
                gas_limit=int(1e6),  # Plenty of gas limit for transactions
                # Try 5 times when creating checkpoints for advancing time transactions
                advance_time_create_checkpoint_retry_count=5,
            )
            fuzz_profit_check(chain_config, parsed_args.steth, pause_on_fail=parsed_args.pause_on_fail)
        except FuzzAssertionException:
            pass
        except Exception as e:  # pylint: disable=broad-except
            print("Unexpected error:\n", repr(e))
            rollbar.report_exc_info(level="critical")
            if parsed_args.pause_on_fail:
                # We don't log info from logging, so we print to ensure this shows up
                # TODO we don't have access to the hyperdrive pool here, ideally we would
                # report it here
                print(f"Pausing pool (port:{chain_port}) crash {repr(e)}")
                while True:
                    time.sleep(1000000)

        time.sleep(1)

        try:
            print("Running fuzz present value test")
            chain_config = LocalChain.Config(
                db_port=db_port,
                chain_host=chain_host,
                chain_port=chain_port,
                log_filename=".logging/fuzz_present_value.log",
                log_to_stdout=False,
                gas_limit=int(1e6),  # Plenty of gas limit for transactions
                # Try 5 times when creating checkpoints for advancing time transactions
                advance_time_create_checkpoint_retry_count=5,
            )
            present_value_epsilon = 0.01
            fuzz_present_value(
                test_epsilon=present_value_epsilon,
                chain_config=chain_config,
                steth=parsed_args.steth,
                pause_on_fail=parsed_args.pause_on_fail,
            )
        except FuzzAssertionException:
            pass
        except Exception as e:  # pylint: disable=broad-except
            print("Unexpected error:\n", repr(e))
            rollbar.report_exc_info(level="critical")
            if parsed_args.pause_on_fail:
                # We don't log info from logging, so we print to ensure this shows up
                # TODO we don't have access to the hyperdrive pool here, ideally we would
                # report it here
                print(f"Pausing pool (port:{chain_port}) crash {repr(e)}")
                while True:
                    time.sleep(1000000)

        time.sleep(1)

        num_checks += 1
        if parsed_args.number_of_runs > 0 and num_checks >= parsed_args.number_of_runs:
            break


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    number_of_runs: int
    pause_on_fail: bool
    chain_host: str
    chain_port: int
    steth: bool


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
        pause_on_fail=namespace.pause_on_fail,
        chain_host=namespace.chain_host,
        chain_port=namespace.chain_port,
        steth=namespace.steth,
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
        "--number-of-runs",
        type=int,
        default=0,
        help="The number times to run the tests. If not set, will run forever.",
    )
    parser.add_argument(
        "--steth",
        default=False,
        action="store_true",
        help="Runs fuzz testing on the steth hyperdrive",
    )
    parser.add_argument(
        "--chain-host",
        type=str,
        default="",
        help="The host to bind for the anvil chain. Defaults to 127.0.0.1.",
    )
    parser.add_argument(
        "--chain-port",
        type=int,
        default=-1,
        help="The port to run anvil on.",
    )
    parser.add_argument(
        "--pause-on-fail",
        default=False,
        action="store_true",
        help="Pause execution on invariance failure.",
    )
    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    main()
