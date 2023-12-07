"""Script to verify that the state of pool reserves is invariant to the order in which positions are closed."""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import asdict
from typing import Any, NamedTuple, Sequence

import pandas as pd
from hyperlogs import ExtendedJSONEncoder

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


def fuzz_path_independence(num_trades: int, num_paths_checked: int, chain_config: LocalChain.Config):
    """Does fuzzy invariant checks for opening and closing longs and shorts.

    Parameters
    ----------
    num_trades: int
        Number of trades to perform during the fuzz tests.
    num_paths_checked: int
        Number of paths (order of operations for opening/closing) to perform.
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.

    Raises
    ------
    AssertionError
        If the invariant checks fail during the tests an error will be raised.
    """
    log_filename = ".logging/fuzz_path_independence.log"
    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(log_filename, chain_config)

    # Generate a list of agents that execute random trades
    trade_list = generate_trade_list(num_trades, rng, interactive_hyperdrive)

    # Open some trades
    trade_events = open_random_trades(trade_list, chain, rng, interactive_hyperdrive, advance_time=True)

    # Snapshot the chain, so we can load the snapshot & close in different orders
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
    check_data: dict[str, Any] | None = None
    first_run_state_dump_dir: str | None = None
    for iteration in range(num_paths_checked):
        print(f"{iteration=}")
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
            if invariant_check_failed(check_data, random_seed, interactive_hyperdrive, chain, first_run_state_dump_dir):
                chain.cleanup()
                raise AssertionError(f"Testing failed; see logs in {log_filename}")
    chain.cleanup()


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    num_trades: int
    num_paths_checked: int
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
        chain_config=LocalChain.Config(chain_port=namespace.chain_port),
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
    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv
    return namespace_to_args(parser.parse_args())


def invariant_check_failed(
    check_data: dict[str, Any],
    random_seed: int,
    interactive_hyperdrive: InteractiveHyperdrive,
    chain: LocalChain,
    first_run_state_dump_dir: str,
) -> bool:
    """Check the pool state invariants.

    Arguments
    ---------
    check_data: dict[str, Any]
        The trade data to check.
    random_seed: int
        Random seed used to run the experiment.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    chain: LocalChain
        An instantiated LocalChain object.
    first_run_state_dump_dir: str
        The directory of the initial run of path independence state dump.

    Returns
    -------
    bool
        If true, at least one of the checks failed.
    """
    failed = False
    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()

    # Base balance
    if check_data["hyperdrive_base_balance"] != pool_state.hyperdrive_base_balance:
        logging.critical(
            "check_data['hyperdrive_base_balance']=%s != pool_state.hyperdrive_base_balance=%s",
            check_data["hyperdrive_base_balance"],
            pool_state.hyperdrive_base_balance,
        )
        failed = True
        # Effective share reserves
    if check_data[
        "effective_share_reserves"
    ] != interactive_hyperdrive.hyperdrive_interface.calc_effective_share_reserves(pool_state):
        logging.critical(
            "check_data['effective_share_reserves']=%s != effective_share_reserves=%s",
            check_data["effective_share_reserves"],
            interactive_hyperdrive.hyperdrive_interface.calc_effective_share_reserves(pool_state),
        )
        failed = True
        # Vault shares (Hyperdrive balance of vault contract)
    if check_data["vault_shares"] != pool_state.vault_shares:
        logging.critical(
            "check_data['vault_shares']=%s != pool_state.vault_shares=%s",
            check_data["vault_shares"],
            pool_state.vault_shares,
        )
        failed = True
        # Minimum share reserves
    if check_data["minimum_share_reserves"] != pool_state.pool_config.minimum_share_reserves:
        logging.critical(
            "check_data['minimum_share_reserves']=%s != pool_state.pool_config.minimum_share_reserves=%s",
            check_data["minimum_share_reserves"],
            pool_state.pool_config.minimum_share_reserves,
        )
        failed = True
        # Check that the subset of columns in initial db pool state and the latest pool state are equal
    if not check_data["initial_pool_state_df"].equals(check_data["final_pool_state_df"]):
        try:
            pd.testing.assert_series_equal(
                check_data["initial_pool_state_df"], check_data["final_pool_state_df"], check_names=False
            )
        except AssertionError as err:
            logging.critical("Database pool info is not equal\n%s", err)
        failed = True

    if failed:
        dump_state_dir = chain.save_state(save_prefix="fuzz_path_independence")

        logging.info(
            (
                "random_seed = %s\npool_config = %s\n\npool_info = %s"
                "\n\nlatest_checkpoint = %s\n\nadditional_info = %s"
            ),
            random_seed,
            json.dumps(asdict(pool_state.pool_config), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(asdict(pool_state.pool_info), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(asdict(pool_state.checkpoint), indent=2, cls=ExtendedJSONEncoder),
            json.dumps(
                {
                    "first_run_state_dump_dir": first_run_state_dump_dir,
                    "dump_state_dir": dump_state_dir,
                    "hyperdrive_address": interactive_hyperdrive.hyperdrive_interface.hyperdrive_contract.address,
                    "base_token_address": interactive_hyperdrive.hyperdrive_interface.base_token_contract.address,
                    "spot_price": interactive_hyperdrive.hyperdrive_interface.calc_spot_price(pool_state),
                    "fixed_rate": interactive_hyperdrive.hyperdrive_interface.calc_fixed_rate(pool_state),
                    "variable_rate": pool_state.variable_rate,
                    "vault_shares": pool_state.vault_shares,
                },
                indent=2,
                cls=ExtendedJSONEncoder,
            ),
        )
    return failed


if __name__ == "__main__":
    main()