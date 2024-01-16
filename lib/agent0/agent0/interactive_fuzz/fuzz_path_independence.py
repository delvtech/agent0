"""Script to verify that the state of pool reserves is invariant to the order in which positions are closed.

# Test procedure
- spin up local chain, deploy hyperdrive
- generate a list of random trades
  - type in [open_short, open_long]
  - amount in uniform[min_trade_amount, max_trade_amount) base
- open those trades in a random order & advance time randomly between
  - maximum time advance between first and last trade is in [0, position_duration)
- save a snapshot of the current chain state
- repeat N times (where N is set as a command-line arg):
    - load chain state (trades are opened, none are closed)
    - close the trades in a random order
    - invariance checks

# Invariance checks (these should be True):
# We are checking that the pool ends up in the same sate regardless of close transaction order
- the following state values should equal in all checks:
  - effective share reserves 
  - shorts outstanding
  - withdrawal shares proceeds
  - share price
  - long exposure
  - bond reserves
  - lp total supply
  - longs outstanding
"""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, NamedTuple, Sequence

import pandas as pd
from fixedpointmath import FixedPoint

from agent0.hyperdrive.crash_report import build_crash_trade_result, log_hyperdrive_crash_report
from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.interactive_fuzz.helpers import (
    FuzzAssertionException,
    close_random_trades,
    execute_random_trades,
    fp_isclose,
    setup_fuzz,
)


# pylint: disable=too-many-locals
def main(argv: Sequence[str] | None = None):
    """Primary entrypoint.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    # Setup the experiment
    parsed_args = parse_arguments(argv)
    fuzz_path_independence(*parsed_args)


def fuzz_path_independence(
    num_trades: int,
    num_paths_checked: int,
    effective_share_reserves_epsilon: float,
    present_value_epsilon: float,
    chain_config: LocalChain.Config,
    log_to_stdout: bool = False,
):
    """Does fuzzy invariant checks for opening and closing longs and shorts.

    Parameters
    ----------
    num_trades: int
        Number of trades to perform during the fuzz tests.
    num_paths_checked: int
        Number of paths (order of operations for opening/closing) to perform.
    effective_share_reserves_epsilon: float
        The allowed error for effective share reserves equality tests.
    present_value_epsilon: float
        The allowed error for present value equality tests.
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.
    log_to_stdout: bool, optional
        If True, log to stdout in addition to a file.
        Defaults to False.
    """
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-arguments
    log_filename = ".logging/fuzz_path_independence.log"
    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(
        log_filename,
        chain_config,
        log_to_stdout,
        log_to_rollbar=False,  # We don't log other crashes to rollbar since we expect failed paths here
        fees=False,
    )

    # Open some trades
    logging.info("Open random trades...")
    trade_events = execute_random_trades(num_trades, chain, rng, interactive_hyperdrive, advance_time=True)
    assert len(trade_events) > 0
    agent = trade_events[0][0]

    # All positions open, we set variable rate to 0 for closing all positions
    interactive_hyperdrive.set_variable_rate(FixedPoint(0))

    # Snapshot the chain, so we can load the snapshot & close in different orders
    logging.info("Save chain snapshot...")
    chain.save_snapshot()

    # List of columns in pool info to check between the initial pool info and the latest pool info.
    check_columns = [
        "shorts_outstanding",
        "withdrawal_shares_proceeds",
        "share_price",
        "long_exposure",
        "bond_reserves",
        "lp_total_supply",
        "longs_outstanding",
    ]

    # Close the trades randomly & verify that the final state is unchanged
    logging.info("Close trades in random order; check final state...")
    check_data: dict[str, Any] | None = None
    first_run_state_dump_dir: str | None = None
    first_run_ticker: pd.DataFrame | None = None
    for iteration in range(num_paths_checked):
        print(f"{iteration=}")
        logging.info("iteration %s out of %s", iteration, num_paths_checked - 1)
        # Load the snapshot
        chain.load_snapshot()

        # Randomly grab some trades & close them one at a time
        # guarantee closing trades within the same checkpoint by getting the checkpoint id before
        # and after closing trades, then asserting they're the same
        starting_checkpoint_id = interactive_hyperdrive.hyperdrive_interface.calc_checkpoint_id()
        close_random_trades(trade_events, rng)
        ending_checkpoint_id = interactive_hyperdrive.hyperdrive_interface.calc_checkpoint_id()
        assert starting_checkpoint_id == ending_checkpoint_id

        # Check the reserve amounts; they should be unchanged now that all of the trades are closed
        pool_state_df = interactive_hyperdrive.get_pool_state(coerce_float=False)

        # On first run, save final state
        if check_data is None:
            check_data = {}
            pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
            check_data["present_value"] = interactive_hyperdrive.hyperdrive_interface.calc_present_value(pool_state)
            check_data[
                "effective_share_reserves"
            ] = interactive_hyperdrive.hyperdrive_interface.calc_effective_share_reserves(pool_state)
            check_data["initial_pool_state_df"] = pool_state_df[check_columns].iloc[-1].copy()
            check_data["hyperdrive_base_balance"] = pool_state.hyperdrive_base_balance
            check_data["minimum_share_reserves"] = pool_state.pool_config.minimum_share_reserves
            check_data["curr_checkpoint_id"] = ending_checkpoint_id
            first_run_state_dump_dir = chain.save_state(save_prefix="fuzz_path_independence")
            first_run_ticker = interactive_hyperdrive.get_ticker()

        # On subsequent run, check against the saved final state
        else:
            # Sanity check, ensure checkpoint id is the same after all runs
            assert ending_checkpoint_id == check_data["curr_checkpoint_id"]

            # Check values not provided in the database
            check_data["final_pool_state_df"] = pool_state_df[check_columns].iloc[-1].copy()
            # Raise an error if it failed
            assert first_run_state_dump_dir is not None
            try:
                invariant_check(
                    check_data, effective_share_reserves_epsilon, present_value_epsilon, interactive_hyperdrive
                )
            except FuzzAssertionException as error:
                dump_state_dir = chain.save_state(save_prefix="fuzz_path_independence")

                # The additional information going into the crash report
                additional_info = {
                    "fuzz_random_seed": random_seed,
                    "first_run_state_dump_dir": first_run_state_dump_dir,
                    "dump_state_dir": dump_state_dir,
                    "first_run_trade_ticker": first_run_ticker,
                    "trade_ticker": interactive_hyperdrive.get_ticker(),
                }
                additional_info.update(error.exception_data)

                # The subset of information going into rollbar
                rollbar_data = {
                    "fuzz_random_seed": random_seed,
                    "first_run_state_dump_dir": first_run_state_dump_dir,
                    "dump_state_dir": dump_state_dir,
                }
                rollbar_data.update(error.exception_data)

                report = build_crash_trade_result(
                    error, interactive_hyperdrive.hyperdrive_interface, agent.agent, additional_info=additional_info
                )
                # Crash reporting already going to file in logging
                log_hyperdrive_crash_report(
                    report,
                    crash_report_to_file=True,
                    crash_report_file_prefix="fuzz_path_independence",
                    log_to_rollbar=True,
                    rollbar_data=rollbar_data,
                )
                chain.cleanup()
                raise error
    chain.cleanup()
    logging.info("Test passed!")


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    num_trades: int
    num_paths_checked: int
    effective_share_reserves_epsilon: float
    present_value_epsilon: float
    chain_config: LocalChain.Config
    log_to_stdout: bool


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
        num_trades=namespace.num_trades,
        num_paths_checked=namespace.num_paths_checked,
        effective_share_reserves_epsilon=namespace.effective_share_reserves_epsilon,
        present_value_epsilon=namespace.present_value_epsilon,
        chain_config=LocalChain.Config(chain_port=namespace.chain_port),
        log_to_stdout=namespace.log_to_stdout,
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
        "--num_trades",
        type=int,
        default=5,
        help="The number of random trades to open.",
    )
    parser.add_argument(
        "--num_paths_checked",
        type=int,
        default=10,
        help="The port to use for the local chain.",
    )
    parser.add_argument(
        "--effective_share_reserves_epsilon",
        type=float,
        default=1e-4,
        help="The allowed error for effective share reserves equality tests.",
    )
    parser.add_argument(
        "--present_value_epsilon",
        type=float,
        default=1e-4,
        help="The allowed error for present value equality tests.",
    )
    parser.add_argument(
        "--chain_port",
        type=int,
        default=10000,
        help="The number of random trades to open.",
    )
    parser.add_argument(
        "--log_to_stdout",
        type=bool,
        default=False,
        help="If True, log to stdout in addition to a file.",
    )
    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


def invariant_check(
    check_data: dict[str, Any],
    effective_share_reserves_epsilon: float,
    present_value_epsilon: float,
    interactive_hyperdrive: InteractiveHyperdrive,
) -> None:
    """Check the pool state invariants and throws an assertion exception if fails.

    Arguments
    ---------
    check_data: dict[str, Any]
        The trade data to check.
    effective_share_reserves_epsilon: float
        The allowed error for effective share reserves equality tests.
    present_value_epsilon: float
        The allowed error for present value equality tests.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    """
    # pylint: disable=too-many-statements
    failed = False
    exception_message: list[str] = ["Fuzz Path Independence Invariant Check"]
    exception_data: dict[str, Any] = {}
    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()

    # Effective share reserves
    expected_effective_share_reserves = FixedPoint(check_data["effective_share_reserves"])
    actual_effective_share_reserves = interactive_hyperdrive.hyperdrive_interface.calc_effective_share_reserves(
        pool_state
    )
    if not fp_isclose(
        expected_effective_share_reserves,
        actual_effective_share_reserves,
        abs_tol=FixedPoint(str(effective_share_reserves_epsilon)),
    ):
        difference_in_wei = abs(
            expected_effective_share_reserves.scaled_value - actual_effective_share_reserves.scaled_value
        )
        exception_message.append(
            f"{expected_effective_share_reserves=} != {actual_effective_share_reserves=}, {difference_in_wei=}"
        )
        exception_data["invariance_check:expected_effective_share_reserves"] = expected_effective_share_reserves
        exception_data["invariance_check:actual_effective_share_reserves"] = actual_effective_share_reserves
        exception_data["invariance_check:effective_share_reserves_difference_in_wei"] = difference_in_wei
        failed = True

    # Present value
    expected_present_value = FixedPoint(check_data["present_value"])
    actual_present_value = interactive_hyperdrive.hyperdrive_interface.calc_present_value(pool_state)
    if not fp_isclose(expected_present_value, actual_present_value, abs_tol=FixedPoint(str(present_value_epsilon))):
        difference_in_wei = abs(expected_present_value.scaled_value - actual_present_value.scaled_value)
        exception_message.append(f"{expected_present_value=} != {actual_present_value=}, {difference_in_wei=}")
        exception_data["invariance_check:expected_present_value"] = expected_present_value
        exception_data["invariance_check:actual_present_value"] = actual_present_value
        exception_data["invariance_check:effective_present_value_difference_in_wei"] = difference_in_wei
        failed = True

    # Check that the subset of columns in initial db pool state and the latest pool state are equal
    expected_pool_state_df = check_data["initial_pool_state_df"]
    actual_pool_state_df = check_data["final_pool_state_df"]
    # Fill values fill nan values with 0 for equality check
    eq_vals = expected_pool_state_df.eq(actual_pool_state_df, fill_value=0)
    if not eq_vals.all():
        # Get rows where values are not equal
        expected_pool_state_df = expected_pool_state_df[~eq_vals]
        actual_pool_state_df = actual_pool_state_df[~eq_vals]
        # Iterate and build exception message and data
        for field_name, expected_val in expected_pool_state_df.items():
            expected_val = FixedPoint(expected_val)
            actual_val = FixedPoint(actual_pool_state_df[field_name])
            difference_in_wei = abs(expected_val.scaled_value - actual_val.scaled_value)
            exception_message.append(
                f"expected_{field_name}={expected_val}, actual_{field_name}={actual_val}, {difference_in_wei=}"
            )
            exception_data["invariance_check:expected_" + field_name] = expected_val
            exception_data["invariance_check:actual_" + field_name] = actual_val
            exception_data["invariance_check:" + field_name + "_difference_in_wei"] = difference_in_wei
        failed = True

    if failed:
        logging.critical("\n".join(exception_message))
        raise FuzzAssertionException(*exception_message, exception_data=exception_data)


if __name__ == "__main__":
    main()
