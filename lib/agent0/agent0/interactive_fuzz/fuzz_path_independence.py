"""Script to verify that the state of pool reserves is invariant to the order in which positions are closed."""
from __future__ import annotations

import argparse
import logging
import sys
from typing import Any, NamedTuple, Sequence

import pandas as pd

from agent0.hyperdrive.crash_report import build_crash_trade_result, log_hyperdrive_crash_report
from agent0.hyperdrive.interactive import InteractiveHyperdrive, LocalChain
from agent0.interactive_fuzz.helpers import close_random_trades, generate_trade_list, open_random_trades, setup_fuzz


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

    Raises
    ------
    AssertionError
        If the invariant checks fail during the tests an error will be raised.
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
            except AssertionError as error:
                dump_state_dir = chain.save_state(save_prefix="fuzz_path_independence")
                additional_info = {
                    "fuzz_random_seed": random_seed,
                    "first_run_state_dump_dir": first_run_state_dump_dir,
                    "dump_state_dir": dump_state_dir,
                }
                report = build_crash_trade_result(
                    error, agent.agent, interactive_hyperdrive.hyperdrive_interface, additional_info=additional_info
                )
                # Crash reporting already going to file in logging
                log_hyperdrive_crash_report(report, crash_report_to_file=False, log_to_rollbar=True)
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
    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()

    # Base balance
    if check_data["hyperdrive_base_balance"] != pool_state.hyperdrive_base_balance:
        exception_message.append(f"{check_data['hyperdrive_base_balance']=} != {pool_state.hyperdrive_base_balance=}")

    # Effective share reserves
    effective_share_reserves = interactive_hyperdrive.hyperdrive_interface.calc_effective_share_reserves(pool_state)
    if check_data["effective_share_reserves"] != effective_share_reserves:
        exception_message.append(f"{check_data['effective_share_reserves']=} != {effective_share_reserves=}")
        failed = True

    # Vault shares (Hyperdrive balance of vault contract)
    if check_data["vault_shares"] != pool_state.vault_shares:
        exception_message.append(f"{check_data['vault_shares']=} != {pool_state.vault_shares=}")
        failed = True

    # Minimum share reserves
    if check_data["minimum_share_reserves"] != pool_state.pool_config.minimum_share_reserves:
        exception_message.append(
            f"{check_data['minimum_share_reserves']=} != {pool_state.pool_config.minimum_share_reserves=}"
        )
        failed = True

    # Check that the subset of columns in initial db pool state and the latest pool state are equal
    if not check_data["initial_pool_state_df"].equals(check_data["final_pool_state_df"]):
        try:
            pd.testing.assert_series_equal(
                check_data["initial_pool_state_df"], check_data["final_pool_state_df"], check_names=False
            )
        except AssertionError as err:
            exception_message.append(f"Database pool info is not equal\n{err=}")
        failed = True

    if failed:
        raise AssertionError(*exception_message)


if __name__ == "__main__":
    main()
