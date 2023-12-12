"""Fuzz test to verify that if all of the funds are removed from Hyperdrive, there is no base left in the contract."""
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

# main script has a lot of stuff going on
# pylint: disable=too-many-locals


def main(argv: Sequence[str] | None = None):
    """Primary entrypoint.

    Arguments
    ---------
    argv: Sequence[str]
        The argv values returned from argparser.
    """
    # Setup the environment
    parsed_args = parse_arguments(argv)
    fuzz_hyperdrive_balance(*parsed_args)


def fuzz_hyperdrive_balance(num_trades: int, chain_config: LocalChain.Config, log_to_stdout: bool = False):
    """Does fuzzy invariant checks on the hyperdrive contract's balances.

    Parameters
    ----------
    num_trades: int
        Number of trades to perform during the fuzz tests.
    chain_config: LocalChain.Config, optional
        Configuration options for the local chain.
    log_to_stdout: bool, optional
        If True, log to stdout in addition to a file.
        Defaults to False.
    """

    log_filename = ".logging/fuzz_hyperdrive_balance.log"
    chain, random_seed, rng, interactive_hyperdrive = setup_fuzz(log_filename, chain_config, log_to_stdout)

    # Get initial vault shares
    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
    initial_vault_shares = pool_state.vault_shares

    # Generate a list of agents that execute random trades
    trade_list = generate_trade_list(num_trades, rng, interactive_hyperdrive)

    # Open some trades
    trade_events = open_random_trades(trade_list, chain, rng, interactive_hyperdrive, advance_time=True)

    # Close the trades
    close_random_trades(trade_events, rng)

    assert len(trade_list) > 0
    agent = trade_list[0][0]

    # Check the reserve amounts; they should be unchanged now that all of the trades are closed
    try:
        invariant_check(initial_vault_shares, interactive_hyperdrive)
    except FuzzAssertionException as error:
        dump_state_dir = chain.save_state(save_prefix="fuzz_long_short_maturity_values")
        additional_info = {"fuzz_random_seed": random_seed, "dump_state_dir": dump_state_dir}
        additional_info.update(error.exception_data)
        report = build_crash_trade_result(
            error, interactive_hyperdrive.hyperdrive_interface, agent.agent, additional_info=additional_info
        )
        # Crash reporting already going to file in logging
        log_hyperdrive_crash_report(
            report, crash_report_to_file=True, crash_report_file_prefix="fuzz_hyperdrive_balance", log_to_rollbar=True
        )
        chain.cleanup()
        raise error
    chain.cleanup()


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    num_trades: int
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
        "--chain_port",
        type=int,
        default=10000,
        help="The port to use for the local chain.",
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
    initial_vault_shares: FixedPoint,
    interactive_hyperdrive: InteractiveHyperdrive,
) -> None:
    """Check the pool state invariants and throws an assertion exception if fails.

    Arguments
    ---------
    initial_vault_shares: FixedPoint
        The number of vault shares owned by the Hyperdrive pool when it was deployed.
    interactive_hyperdrive: InteractiveHyperdrive
        An instantiated InteractiveHyperdrive object.
    """
    failed = False
    exception_message: list[str] = ["Fuzz Hyperdrive Balance Invariant Check"]
    exception_data: dict[str, Any] = {}

    pool_state = interactive_hyperdrive.hyperdrive_interface.get_hyperdrive_state()
    vault_shares = pool_state.vault_shares
    if vault_shares != initial_vault_shares:
        difference_in_wei = abs(vault_shares.scaled_value - initial_vault_shares.scaled_value)
        exception_message.append(f"{vault_shares=} != {initial_vault_shares=}, {difference_in_wei=}")
        exception_data["invariance_check:vault_shares"] = vault_shares
        exception_data["invariance_check:initial_vault_shares"] = initial_vault_shares
        exception_data["invariance_check:vault_shares_difference_in_wei"] = difference_in_wei
        failed = True

    share_reserves = pool_state.pool_info.share_reserves
    minimum_share_reserves = pool_state.pool_config.minimum_share_reserves
    if share_reserves < minimum_share_reserves:
        difference_in_wei = abs(share_reserves.scaled_value - minimum_share_reserves.scaled_value)
        exception_message.append(f"{share_reserves=} < {minimum_share_reserves=}")
        exception_data["invariance_check:share_reserves"] = share_reserves
        exception_data["invariance_check:minimum_share_reserves"] = minimum_share_reserves
        exception_data["invariance_check:share_reserves_difference_in_wei"] = difference_in_wei

        failed = True

    if failed:
        logging.critical("\n".join(exception_message))
        raise FuzzAssertionException(*exception_message, exception_data=exception_data)


if __name__ == "__main__":
    main()
