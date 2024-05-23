"""Script to verify that the state of pool reserves is invariant to the order in which positions are closed.

# Test procedure
- spin up local chain, deploy hyperdrive without fees
- execute random trades
  - from [open_long, open_short]
  - trade amount in uniform[min_trade_amount, max_trade_amount) base
  - advance one block (12 sec) betwen each trade.
  - advance time randomly between trades
  - the maximum time advance between first and last trade is in [0, position_duration)
- set the variable rate to 0
- save a snapshot of the current chain state
- repeat N times (where N is set as a command-line arg):
    - load chain state (all trades are opened, none are closed)
    - close the trades in a random order
    - invariance checks

# Invariance checks (these should be True):
# We are checking that the pool ends up in the same sate regardless of close transaction order
- the following state values should equal in all checks:
  - effective share reserves 
  - present value
  - shorts outstanding
  - withdrawal shares proceeds
  - lp share price
  - long exposure
  - bond reserves
  - lp total supply
  - longs outstanding
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from math import perm
from typing import Any, NamedTuple, Sequence

import pandas as pd
import rollbar
from fixedpointmath import FixedPoint, isclose

from agent0.core.hyperdrive.crash_report import build_crash_trade_result, log_hyperdrive_crash_report
from agent0.core.hyperdrive.interactive import LocalChain, LocalHyperdrive
from agent0.ethpy.base.errors import ContractCallException
from agent0.hyperfuzz import FuzzAssertionException
from agent0.hyperlogs import ExtendedJSONEncoder

from .helpers import close_trades, execute_random_trades, permute_trade_events, setup_fuzz


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
    lp_share_price_epsilon: float,
    effective_share_reserves_epsilon: float,
    present_value_epsilon: float,
    chain_config: LocalChain.Config,
):
    """Does fuzzy invariant checks for opening and closing longs and shorts.

    Parameters
    ----------
    num_trades: int
        Number of trades to perform during the fuzz tests.
    num_paths_checked: int
        Number of paths (order of operations for opening/closing) to perform.
    lp_share_price_epsilon: float
        The allowed error for LP share price equality tests.
    effective_share_reserves_epsilon: float
        The allowed error for effective share reserves equality tests.
    present_value_epsilon: float
        The allowed error for present value equality tests.
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.
    """
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-arguments

    # Make sure there exists enough permutations of paths to ensure independent operations
    # plus some buffer
    if perm(num_trades) < 2 * num_paths_checked:
        raise AssertionError("Need more trades to check {num_paths_checked} paths.")

    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(
        chain_config,
        # Trade crashes in this file have expected failures, hence we log interactive
        # hyperdrive crashes as info instead of critical.
        crash_log_level=logging.INFO,
        curve_fee=FixedPoint(0),
        flat_fee=FixedPoint(0),
        governance_lp_fee=FixedPoint(0),
        governance_zombie_fee=FixedPoint(0),
        fuzz_test_name="fuzz_path_independence",
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

    # Dictionary of columns in pool state to check between the initial pool info and the latest pool info.
    # Keys represents the columns, values represents the allowed error.
    check_columns_epsilon: dict[str, Any] = {
        "shorts_outstanding": 0,
        "withdrawal_shares_proceeds": 0,
        "lp_share_price": lp_share_price_epsilon,
        "long_exposure": 0,
        "bond_reserves": 0,
        "lp_total_supply": 0,
        "longs_outstanding": 0,
    }
    check_columns = list(check_columns_epsilon.keys())
    # Add additional epsilon checks for added invariance checks
    check_columns_epsilon["present_value"] = present_value_epsilon
    check_columns_epsilon["effective_share_reserves"] = effective_share_reserves_epsilon

    # Close the trades randomly & verify that the final state is unchanged
    logging.info("Close trades in random order; check final state...")
    check_data: dict[str, Any] | None = None
    first_run_state_dump_dir: str | None = None
    first_run_ticker: pd.DataFrame | None = None
    invariance_checked: bool = False
    latest_error: Exception | None = None

    # In case all paths failed, we keep track of all tickers and crash reports for all paths

    trade_paths = []
    trade_event_paths = []
    for iteration in range(num_paths_checked):
        print(f"{iteration=}")
        logging.info("iteration %s out of %s", iteration, num_paths_checked - 1)
        # Load the snapshot
        chain.load_snapshot()

        # Generate a random permutation of the trades
        # Resample if duplicate
        duplicate = True
        random_trade_events = None
        while duplicate:
            random_trade_events = permute_trade_events(trade_events, rng)
            duplicate = False
            # TODO this is O(x^2), fix
            for trade_path in trade_paths:
                if trade_path == random_trade_events:
                    duplicate = True
                    break

        assert random_trade_events is not None
        trade_paths.append(random_trade_events)

        # Randomly grab some trades & close them one at a time
        # guarantee closing trades within the same checkpoint by getting the checkpoint id before
        # and after closing trades, then asserting they're the same
        starting_checkpoint_id = interactive_hyperdrive.interface.calc_checkpoint_id()
        try:
            close_trades(random_trade_events)
        except ContractCallException:
            # Trades can fail here due to invalid order, we ignore and move on
            # These trades get logged as info
            # We track the ticker for each failed path here. This bookkeeping is only
            # used if all paths fail
            trade_event_paths.append(interactive_hyperdrive.get_trade_events())
            continue

        ending_checkpoint_id = interactive_hyperdrive.interface.calc_checkpoint_id()
        if starting_checkpoint_id != ending_checkpoint_id:
            message = "Trades were not closed in the same checkpoint"
            logging.warning(message)
            rollbar_data = {"fuzz_random_seed": random_seed}
            rollbar.report_message(message, "warning", extra_data=rollbar_data)
            continue

        # Check the reserve amounts; they should be unchanged now that all of the trades are closed
        pool_state_df = interactive_hyperdrive.get_pool_info(coerce_float=False)

        # On first run, save final state
        if check_data is None:
            check_data = {}
            pool_state = interactive_hyperdrive.interface.get_hyperdrive_state()
            check_data["present_value"] = interactive_hyperdrive.interface.calc_present_value(pool_state)
            check_data["effective_share_reserves"] = interactive_hyperdrive.interface.calc_effective_share_reserves(
                pool_state
            )
            check_data["initial_pool_state"] = pool_state_df[check_columns].iloc[-1].copy()
            check_data["hyperdrive_base_balance"] = pool_state.hyperdrive_base_balance
            check_data["minimum_share_reserves"] = pool_state.pool_config.minimum_share_reserves
            check_data["curr_checkpoint_id"] = ending_checkpoint_id
            first_run_state_dump_dir = str(chain.save_state(save_prefix="fuzz_path_independence"))
            first_run_ticker = interactive_hyperdrive.get_trade_events()

        # On subsequent run, check against the saved final state
        else:
            invariance_checked = True
            # Sanity check, ensure checkpoint id is the same after all runs
            assert ending_checkpoint_id == check_data["curr_checkpoint_id"]

            # Check values not provided in the database
            check_data["final_pool_state"] = pool_state_df[check_columns].iloc[-1].copy()

            # Raise an error if it failed
            assert first_run_state_dump_dir is not None
            try:
                invariant_check(check_data, check_columns_epsilon, interactive_hyperdrive)
            except FuzzAssertionException as error:
                dump_state_dir = chain.save_state(save_prefix="fuzz_path_independence")

                # The additional information going into the crash report
                additional_info = {
                    "fuzz_random_seed": random_seed,
                    "first_run_state_dump_dir": first_run_state_dump_dir,
                    "dump_state_dir": dump_state_dir,
                    "first_run_trade_ticker": first_run_ticker,
                    "trade_events": interactive_hyperdrive.get_trade_events(),
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
                    error, interactive_hyperdrive.interface, agent.account, additional_info=additional_info
                )
                # Crash reporting already going to file in logging
                log_hyperdrive_crash_report(
                    report,
                    crash_report_to_file=True,
                    crash_report_file_prefix="fuzz_path_independence",
                    log_to_rollbar=True,
                    rollbar_data=rollbar_data,
                )
                latest_error = error

    # If the number of successful paths < 2, we print and log a warning
    if not invariance_checked:
        warning_message = "No invariance checks were performed due to failed paths."
        logging.warning(warning_message)
        rollbar_data = {
            "fuzz_random_seed": random_seed,
            "close_random_paths": [[trade for _, trade in path] for path in trade_paths],
            "trade_event_paths": trade_event_paths,
        }
        rollbar.report_message(
            warning_message,
            "warning",
            extra_data=json.loads(json.dumps(rollbar_data, indent=2, cls=ExtendedJSONEncoder)),
        )

    # If any of the path checks broke, we throw an exception at the very end
    if latest_error is not None:
        chain.cleanup()
        raise latest_error

    chain.cleanup()
    logging.info("Test passed!")


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    num_trades: int
    num_paths_checked: int
    lp_share_price_epsilon: float
    effective_share_reserves_epsilon: float
    present_value_epsilon: float
    chain_config: LocalChain.Config


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
        lp_share_price_epsilon=namespace.lp_share_price_epsilon,
        effective_share_reserves_epsilon=namespace.effective_share_reserves_epsilon,
        present_value_epsilon=namespace.present_value_epsilon,
        chain_config=LocalChain.Config(chain_port=namespace.chain_port, log_to_stdout=namespace.log_to_stdout),
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
        "--lp_share_price_epsilon",
        type=float,
        default=1e-14,
        help="The allowed error for lp share price equality tests.",
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
    check_epsilon: dict[str, Any],
    interactive_hyperdrive: LocalHyperdrive,
) -> None:
    """Check the pool state invariants and throws an assertion exception if fails.

    Arguments
    ---------
    check_data: dict[str, Any]
        The trade data to check.
    check_epsilon: dict[str, Any]
        The expected epsilon for each invariants check.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    """
    # pylint: disable=too-many-statements
    failed = False
    exception_message: list[str] = ["Fuzz Path Independence Invariant Check"]
    exception_data: dict[str, Any] = {}
    pool_state = interactive_hyperdrive.interface.get_hyperdrive_state()

    # Effective share reserves
    expected_effective_share_reserves = FixedPoint(check_data["effective_share_reserves"])
    actual_effective_share_reserves = interactive_hyperdrive.interface.calc_effective_share_reserves(pool_state)
    if not isclose(
        expected_effective_share_reserves,
        actual_effective_share_reserves,
        abs_tol=FixedPoint(str(check_epsilon["effective_share_reserves"])),
    ):
        difference_in_wei = abs(
            expected_effective_share_reserves.scaled_value - actual_effective_share_reserves.scaled_value
        )
        exception_message.append("The effective share reserves has deviated after closing all trades.")
        exception_message.append(
            f"{expected_effective_share_reserves=} != {actual_effective_share_reserves=}, {difference_in_wei=}"
        )
        exception_data["invariance_check:expected_effective_share_reserves"] = expected_effective_share_reserves
        exception_data["invariance_check:actual_effective_share_reserves"] = actual_effective_share_reserves
        exception_data["invariance_check:effective_share_reserves_difference_in_wei"] = difference_in_wei
        failed = True

    # Present value
    expected_present_value = FixedPoint(check_data["present_value"])
    actual_present_value = interactive_hyperdrive.interface.calc_present_value(pool_state)
    if not isclose(
        expected_present_value, actual_present_value, abs_tol=FixedPoint(str(check_epsilon["present_value"]))
    ):
        difference_in_wei = abs(expected_present_value.scaled_value - actual_present_value.scaled_value)
        exception_message.append("The present value has deviated after closing all trades.")
        exception_message.append(f"{expected_present_value=} != {actual_present_value=}, {difference_in_wei=}")
        exception_data["invariance_check:expected_present_value"] = expected_present_value
        exception_data["invariance_check:actual_present_value"] = actual_present_value
        exception_data["invariance_check:effective_present_value_difference_in_wei"] = difference_in_wei
        failed = True

    # Check that the subset of columns in initial db pool state and the latest pool state are equal
    expected_pool_state: pd.Series = check_data["initial_pool_state"]
    actual_pool_state: pd.Series = check_data["final_pool_state"]

    # Sanity check, both series have the same indices
    assert (expected_pool_state.index == actual_pool_state.index).all()

    for field_name, expected_val in expected_pool_state.items():
        field_name = str(field_name)
        expected_val = FixedPoint(expected_val)
        actual_val = FixedPoint(actual_pool_state[field_name])
        epsilon = FixedPoint(str(check_epsilon[field_name]))
        if not isclose(expected_val, actual_val, abs_tol=epsilon):
            difference_in_wei = abs(expected_val.scaled_value - actual_val.scaled_value)
            exception_message.append("The pool state has deviated after closing all of the trades.")
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
