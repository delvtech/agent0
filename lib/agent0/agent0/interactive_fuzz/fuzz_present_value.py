"""Script to confirm present value and LP share price invariance.

# Test procedure
- spin up local chain, deploy hyperdrive
- generate a list of random trades
  - type in [open_short, open_long, add_liquidity, remove_liquidity]
  - amount in uniform[min_trade_amount, max_trade_amount) base
- execute those trades in a random order & advance time randomly between
- check invariances after each trade

# Invariance checks (these should be True):
- the following state values should equal in all checks:
  - for any trade, LP share price shouldn't change by more than 0.1%
  - open or close trades shouldn't affect PV within 0.1
  - removing liquidity shouldn't result in the PV increasing (it should decrease)
  - adding liquidity shouldn't result in the PV decreasing (it should increase)
  - present value should always be >= idle
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
from agent0.hyperdrive.state.hyperdrive_actions import HyperdriveActionType
from agent0.interactive_fuzz.helpers import (
    FuzzAssertionException,
    close_random_trades,
    fp_isclose,
    generate_trade_list,
    open_random_trades,
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
    fuzz_present_value(*parsed_args)


def fuzz_present_value(
    test_epsilon: float,
    chain_config: LocalChain.Config,
    log_to_stdout: bool = False,
):
    """Does fuzzy invariant checks for opening and closing longs and shorts.

    Parameters
    ----------
    test_epsilon: float
        The allowed error for present value equality tests.
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.
    log_to_stdout: bool, optional
        If True, log to stdout in addition to a file.
        Defaults to False.
    """
    log_filename = ".logging/fuzz_path_independence.log"
    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(log_filename, chain_config, log_to_stdout, fees=False)

    initial_pool_state = interactive_hyperdrive.hyperdrive_interface.current_pool_state
    check_data = {
        "lp_share_price": initial_pool_state.pool_info.lp_share_price,
        "present_value": interactive_hyperdrive.hyperdrive_interface.calc_present_value(initial_pool_state),
    }

    for trade_type in [HyperdriveActionType.OPEN_LONG, HyperdriveActionType.CLOSE_LONG, HyperdriveActionType.OPEN_SHORT, HyperdriveActionType.CLOSE_SHORT, HyperdriveActionType.ADD_LIQUIDITY, HyperdriveActionType.REMOVE_LIQUIDITY]:
        

    try:
        invariant_check(check_data, test_epsilon, interactive_hyperdrive)
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

    test_epsilon: float
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
        test_epsilon=namespace.test_epsilon,
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
        "--test_epsilon",
        type=float,
        default=1e-4,
        help="The allowed error for present value and share price equality tests.",
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
    test_epsilon: float,
    interactive_hyperdrive: InteractiveHyperdrive,
) -> None:
    """Check the pool state invariants and throws an assertion exception if fails.

    Arguments
    ---------
    check_data: dict[str, Any]
        The trade data to check.
    test_epsilon: float
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
    if expected_effective_share_reserves != actual_effective_share_reserves:
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
    if not fp_isclose(expected_present_value, actual_present_value, abs_tol=FixedPoint(str(test_epsilon))):
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
