"""Script to verify that the state of pool reserves is invariant to the order in which positions are closed."""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, NamedTuple, Sequence

from fixedpointmath import FixedPoint

from agent0.hyperdrive.crash_report import build_crash_trade_result, log_hyperdrive_crash_report
from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.interactive_fuzz.helpers import (
    FuzzAssertionException,
    close_random_trades,
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
    fuzz_path_independence(*parsed_args)


def fuzz_path_independence(
    num_trades: int,
    num_paths_checked: int,
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
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.
    log_to_stdout: bool, optional
        If True, log to stdout in addition to a file.
        Defaults to False.
    """
    log_filename = ".logging/fuzz_path_independence.log"
    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(log_filename, chain_config, log_to_stdout)

    # Generate a list of agents that execute random trades
    trade_list = generate_trade_list(num_trades, rng, interactive_hyperdrive)

    # Open some trades
    logging.info("Open random trades...")
    trade_events = open_random_trades(trade_list, chain, rng, interactive_hyperdrive, advance_time=True)
    assert len(trade_events) > 0
    agent = trade_events[0][0]

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
    for iteration in range(num_paths_checked):
        print(f"{iteration=}")
        logging.info("iteration %s out of %s", iteration, num_paths_checked - 1)
        # Load the snapshot
        chain.load_snapshot()

        # Randomly grab some trades & close them one at a time
        close_random_trades(trade_events, rng)

        # Check the reserve amounts; they should be unchanged now that all of the trades are closed
        pool_state_df = interactive_hyperdrive.get_pool_state(coerce_float=False)

        # On first run, save final state
        if check_data is None:
            check_data = {}
            pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
            effective_share_reserves = interactive_hyperdrive.hyperdrive_interface.calc_effective_share_reserves(
                pool_state
            )
            check_data["initial_pool_state_df"] = pool_state_df[check_columns].iloc[-1].copy()
            check_data["hyperdrive_base_balance"] = pool_state.hyperdrive_base_balance
            check_data["effective_share_reserves"] = effective_share_reserves
            check_data["vault_shares"] = pool_state.vault_shares
            check_data["minimum_share_reserves"] = pool_state.pool_config.minimum_share_reserves
            first_run_state_dump_dir = chain.save_state(save_prefix="fuzz_path_independence")

        # On subsequent run, check against the saved final state
        else:
            # Check values not provided in the database
            check_data["final_pool_state_df"] = pool_state_df[check_columns].iloc[-1].copy()
            # Raise an error if it failed
            assert first_run_state_dump_dir is not None
            try:
                invariant_check(check_data, interactive_hyperdrive)
            except FuzzAssertionException as error:
                dump_state_dir = chain.save_state(save_prefix="fuzz_path_independence")
                additional_info = {
                    "fuzz_random_seed": random_seed,
                    "first_run_state_dump_dir": first_run_state_dump_dir,
                    "dump_state_dir": dump_state_dir,
                }
                additional_info.update(error.exception_data)
                report = build_crash_trade_result(
                    error, interactive_hyperdrive.hyperdrive_interface, agent.agent, additional_info=additional_info
                )
                # Crash reporting already going to file in logging
                log_hyperdrive_crash_report(
                    report,
                    crash_report_to_file=True,
                    crash_report_file_prefix="fuzz_path_independence",
                    log_to_rollbar=True,
                )
                chain.cleanup()
                raise error
    chain.cleanup()
    logging.info("Test passed!")


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    num_trades: int
    num_paths_checked: int
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
    interactive_hyperdrive: InteractiveHyperdrive,
) -> None:
    """Check the pool state invariants and throws an assertion exception if fails.

    Arguments
    ---------
    check_data: dict[str, Any]
        The trade data to check.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    """
    failed = False
    exception_message: list[str] = ["Fuzz Path Independence Invariant Check"]
    exception_data: dict[str, Any] = {}
    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()

    # Base balance
    expected_base_balance = FixedPoint(check_data["hyperdrive_base_balance"])
    actual_base_balance = pool_state.hyperdrive_base_balance
    if expected_base_balance != actual_base_balance:
        difference_in_wei = abs(expected_base_balance.scaled_value - actual_base_balance.scaled_value)
        exception_message.append(f"{expected_base_balance=} != {actual_base_balance=}, {difference_in_wei=}")
        exception_data["invariance_check:expected_base_balance"] = expected_base_balance
        exception_data["invariance_check:actual_base_balance"] = actual_base_balance
        exception_data["invariance_check:base_balance_difference_in_wei"] = difference_in_wei
        failed = True

    # Effective share reserves
    expected_share_reserves = FixedPoint(check_data["effective_share_reserves"])
    actual_share_reserves = interactive_hyperdrive.hyperdrive_interface.calc_effective_share_reserves(pool_state)
    if expected_share_reserves != actual_share_reserves:
        difference_in_wei = abs(expected_share_reserves.scaled_value - actual_share_reserves.scaled_value)
        exception_message.append(f"{expected_share_reserves=} != {actual_share_reserves=}, {difference_in_wei=}")
        exception_data["invariance_check:expected_share_reserves"] = expected_share_reserves
        exception_data["invariance_check:actual_share_reserves"] = actual_share_reserves
        exception_data["invariance_check:share_reserves_difference_in_wei"] = difference_in_wei
        failed = True

    # Vault shares (Hyperdrive balance of vault contract)
    expected_vault_shares = FixedPoint(check_data["vault_shares"])
    actual_vault_shares = pool_state.vault_shares
    if expected_vault_shares != actual_vault_shares:
        difference_in_wei = abs(expected_vault_shares.scaled_value - actual_vault_shares.scaled_value)
        exception_message.append(f"{expected_vault_shares} != {actual_vault_shares}, {difference_in_wei=}")
        exception_data["invariance_check:expected_vault_shares"] = expected_vault_shares
        exception_data["invariance_check:actual_share_shares"] = actual_vault_shares
        exception_data["invariance_check:vault_shares_difference_in_wei"] = difference_in_wei
        failed = True

    # Minimum share reserves
    expected_minimum_share_reserves = check_data["minimum_share_reserves"]
    actual_minimum_share_reserves = pool_state.pool_config.minimum_share_reserves
    if expected_minimum_share_reserves != actual_minimum_share_reserves:
        difference_in_wei = abs(expected_minimum_share_reserves - actual_minimum_share_reserves)
        exception_message.append(
            f"{expected_minimum_share_reserves} != {actual_minimum_share_reserves}, {difference_in_wei=}"
        )
        exception_data["invariance_check:expected_minimum_share_reserves"] = expected_minimum_share_reserves
        exception_data["invariance_check:actual_minimum_share_reserves"] = actual_minimum_share_reserves
        exception_data["invariance_check:minimum_share_reserves_difference_in_wei"] = difference_in_wei
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
