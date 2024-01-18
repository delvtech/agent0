"""Script for checking Hyperdrive invariants at each block.

This script assumes that fuzz_bots is running in a concurrent process.
Given that, we will periodically run this test:


# Invariance checks (these should be True):
- hyperdrive base & eth balances are zero
- the expected total shares equals the hyperdrive balance in the vault contract
- the pool has more than the minimum share reserves
- the system is solvent, i.e. (share reserves - long exposure in shares - min share reserves) > 0
- if a hyperdrive trade happened then a checkpoint was created at the appropriate time
"""
from __future__ import annotations

import argparse
import logging
import sys
import time
from typing import Any, NamedTuple, Sequence

from eth_typing import BlockNumber
from ethpy import build_eth_config
from ethpy.hyperdrive.interface import HyperdriveReadInterface
from ethpy.hyperdrive.state.pool_state import PoolState
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from hyperlogs import setup_logging
from hyperlogs.rollbar_utilities import initialize_rollbar
from web3.exceptions import BlockNotFound
from web3.types import BlockData

from agent0.base.config import EnvironmentConfig
from agent0.hyperdrive.crash_report import build_crash_trade_result, get_anvil_state_dump, log_hyperdrive_crash_report
from agent0.interactive_fuzz.helpers import FuzzAssertionException, fp_isclose


def main(argv: Sequence[str] | None = None) -> None:
    """Check Hyperdrive invariants each block.

    Arguments
    ---------
    argv: Sequence[str]
        A sequnce containing the uri to the database server and the test epsilon.
    """

    log_to_rollbar = initialize_rollbar("fuzzbots_invariantcheck")

    # Setup the experiment
    parsed_args, interface = setup_fuzz(argv)
    # Run the loop forever
    last_executed_block_number = 0  # no matter what we will run the check the first time
    while True:
        latest_block = interface.get_block("latest")
        latest_block_number = latest_block.get("number", None)
        if latest_block_number is None:
            raise AssertionError("Block has no number.")
        if not latest_block_number > last_executed_block_number:
            # take a nap
            time.sleep(parsed_args.sleep_time)
            continue
        # Update block number
        last_executed_block_number = latest_block_number
        try:
            run_invariant_checks(latest_block, latest_block_number, interface, parsed_args.test_epsilon)
        except FuzzAssertionException as error:
            report = build_crash_trade_result(error, interface, additional_info=error.exception_data)
            report.anvil_state = get_anvil_state_dump(interface.web3)
            rollbar_data = error.exception_data

            log_hyperdrive_crash_report(
                report,
                crash_report_to_file=True,
                crash_report_file_prefix="fuzz_bots_invariant_checks",
                log_to_rollbar=log_to_rollbar,
                rollbar_data=rollbar_data,
            )


def setup_fuzz(argv: Sequence[str] | None) -> tuple[Args, HyperdriveReadInterface]:
    """Setup the fuzz config & interface.

    Arguments
    ---------
    argv: Sequence[str]
        A sequnce containing the uri to the database server and the test epsilon.

    Returns
    -------
    tuple[Args, HyperdriveReadInterface]
        The parsed arguments and interface constructed from those arguments.
    """
    parsed_args = parse_arguments(argv)
    eth_config = build_eth_config(parsed_args.eth_config_env_file)
    env_config = EnvironmentConfig(
        delete_previous_logs=False,
        halt_on_errors=False,
        log_filename=".logging/invariant_checks.log",
        log_level=logging.ERROR,
        log_stdout=False,
        global_random_seed=1234,
        username="INVARIANT_CHECKS",
    )
    # Setup logging
    setup_logging(
        log_filename=env_config.log_filename,
        max_bytes=env_config.max_bytes,
        log_level=env_config.log_level,
        delete_previous_logs=env_config.delete_previous_logs,
        log_stdout=env_config.log_stdout,
        log_format_string=env_config.log_formatter,
    )
    # Setup hyperdrive interface
    interface = HyperdriveReadInterface(eth_config)
    return parsed_args, interface


def run_invariant_checks(
    latest_block: BlockData,
    latest_block_number: BlockNumber,
    interface: HyperdriveReadInterface,
    test_epsilon: float,
) -> None:
    """Run the invariant checks.

    Arguments
    ---------
    latest_block: BlockData
        The current block to be tested.
    latest_block_number: BlockNumber
        The current block number.
    interface: HyperdriveReadInterface
        An instantiated HyperdriveReadInterface object constructed using the script arguments.
    test_epsilon: float
        The tolerance for the invariance checks.
    """
    # Get the variables to check & check each invariant
    pool_state = interface.get_hyperdrive_state(latest_block)
    any_check_failed = False
    exception_message: list[str] = ["Continuous Fuzz Bots Invariant Checks"]
    exception_data: dict[str, Any] = {}

    # Due to inaccuracies with the share_price in pool_state, we call the yield contract's convertToShares
    # function to get a more accurate shorts outstanding in shares
    shorts_outstanding_in_shares = FixedPoint(
        scaled_value=interface.yield_contract.functions.convertToShares(
            pool_state.pool_info.shorts_outstanding.scaled_value
        ).call()
    )

    results: list[InvariantCheckResults] = [
        _check_eth_balances(latest_block_number, pool_state),
        _check_base_balances(latest_block_number, pool_state),
        _check_total_shares(latest_block_number, test_epsilon, pool_state, shorts_outstanding_in_shares),
        _check_minimum_share_reserves(latest_block_number, pool_state),
        _check_solvency(latest_block_number, pool_state),
        _check_present_value_greater_than_idle_shares(latest_block_number, interface, pool_state),
        _check_lp_share_price(latest_block_number, interface, test_epsilon, pool_state),
        _check_checkpointing_should_never_fail(latest_block, latest_block_number, interface, pool_state),
    ]

    for failed, message, data in results:
        any_check_failed = failed | any_check_failed
        if message:
            exception_message.append(message)
        exception_data.update(data)

    # Log additional information if any test failed
    if any_check_failed:
        logging.critical("\n".join(exception_message))
        raise FuzzAssertionException(*exception_message, exception_data=exception_data)


class InvariantCheckResults(NamedTuple):
    """Results from an invariant check."""

    failed: bool
    exception_message: str | None
    exception_data: dict[str, Any]


def _check_eth_balances(block_number: BlockNumber, pool_state: PoolState) -> InvariantCheckResults:
    # Hyperdrive base & eth balances should always be zero
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}

    if pool_state.hyperdrive_eth_balance != FixedPoint(0):
        exception_message = f"{pool_state.hyperdrive_eth_balance} != 0. Test failed at block {block_number}"
        exception_data["invariance_check:actual_hyperdrive_eth_balance"] = pool_state.hyperdrive_eth_balance
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_base_balances(block_number: BlockNumber, pool_state: PoolState) -> InvariantCheckResults:
    # Hyperdrive base & eth balances should always be zero
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}

    if pool_state.hyperdrive_base_balance != FixedPoint(0):
        exception_message = f"{pool_state.hyperdrive_base_balance} != 0. Test failed at block {block_number}"
        exception_data["invariance_check:actual_hyperdrive_base_balance"] = pool_state.hyperdrive_base_balance
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_checkpointing_should_never_fail(
    block: BlockData, block_number: BlockNumber, interface: HyperdriveReadInterface, pool_state: PoolState
) -> InvariantCheckResults:
    # Creating a checkpoint should never fail
    # TODO: add get_block_transactions() to interface
    # NOTE: This wold be prone to false positives.
    #   If the transaction would have failed anyway, then we don't know
    #   that it failed bc of checkpoint failure or bc e.g., open long was for too much
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}

    transactions = block.get("transactions", None)
    if transactions is not None and isinstance(transactions, Sequence):
        # If any transaction is to hyperdrive then assert a checkpoint happened
        for transaction in transactions:
            if isinstance(transaction, HexBytes):
                # If hexbytes, there was no trade
                continue
            txn_to = transaction.get("to", None)
            if txn_to is None:
                raise AssertionError("Transaction did not have a 'to' key.")
            if txn_to == interface.hyperdrive_contract.address and pool_state.checkpoint.share_price <= 0:
                exception_message = (
                    f"A transaction was created but no checkpoint was minted.\n"
                    f"{pool_state.checkpoint.share_price=}\n"
                    f"{transaction=}\n"
                    f"{block_number=}"
                )
                failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_solvency(block_number: BlockNumber, pool_state: PoolState) -> InvariantCheckResults:
    # The system should always be solvent
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}

    solvency = (
        pool_state.pool_info.share_reserves
        - pool_state.pool_info.long_exposure / pool_state.pool_info.share_price
        - pool_state.pool_config.minimum_share_reserves
    )
    if not solvency > FixedPoint(0):
        exception_message = (
            f"{solvency=} <= 0. "
            f"({pool_state.pool_info.share_reserves=} - {pool_state.pool_info.long_exposure=} - "
            f"{pool_state.pool_config.minimum_share_reserves=}). Test failed at block {block_number}."
        )
        exception_data["invariance_check:solvency"] = solvency
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_minimum_share_reserves(block_number: BlockNumber, pool_state: PoolState) -> InvariantCheckResults:
    # The pool has more than the minimum share reserves
    failed = False
    exception_message = ""
    exception_data: dict[str, Any] = {}

    current_share_reserves = pool_state.pool_info.share_reserves
    minimum_share_reserves = pool_state.pool_config.minimum_share_reserves
    if not current_share_reserves >= minimum_share_reserves:
        exception_message = (
            f"{current_share_reserves} < {minimum_share_reserves=}. "
            f"({pool_state.pool_info.share_reserves=} * "
            f"{pool_state.pool_info.share_price=} - "
            f"{pool_state.pool_info.long_exposure=}). "
            f"Test failed at block {block_number}."
        )
        exception_data["invariance_check:current_share_reserves"] = current_share_reserves
        exception_data["invariance_check:minimum_share_reserves"] = minimum_share_reserves
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_total_shares(
    block_number: BlockNumber, test_epsilon: float, pool_state: PoolState, shorts_outstanding_in_shares: FixedPoint
) -> InvariantCheckResults:
    # Total shares is correctly calculated
    failed = False
    exception_message = ""
    exception_data: dict[str, Any] = {}

    expected_vault_shares = (
        pool_state.pool_info.share_reserves
        # The term below replaces this calculation:
        # pool_state.pool_info.shorts_outstanding / pool_state.pool_info.share_price
        + shorts_outstanding_in_shares
        + pool_state.gov_fees_accrued
        + pool_state.pool_info.withdrawal_shares_proceeds
        + pool_state.pool_info.zombie_share_reserves
    )
    actual_vault_shares = pool_state.vault_shares
    if not fp_isclose(expected_vault_shares, actual_vault_shares, abs_tol=FixedPoint(str(test_epsilon))):
        difference_in_wei = abs(expected_vault_shares.scaled_value - actual_vault_shares.scaled_value)
        exception_message = (
            f"{actual_vault_shares=} is incorrect, should be {expected_vault_shares}. "
            f"{difference_in_wei=}. "
            f"Test failed at block {block_number}."
        )
        exception_data["invariance_check:expected_vault_shares"] = expected_vault_shares
        exception_data["invariance_check:actual_vault_shares"] = actual_vault_shares
        exception_data["invariance_check:vault_shares_difference_in_wei"] = difference_in_wei
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_present_value_greater_than_idle_shares(
    block_number: BlockNumber,
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
) -> InvariantCheckResults:
    """Returns True if the test (present_value > idle_shares) fails.

    Arguments
    ---------
    block_number: BlockNumber
    interface: HyperdriveReadInterface
    pool_state: PoolState

    Returns
    -------
    InvariantCheckResults
    """

    failed = False
    exception_message = ""
    exception_data: dict[str, Any] = {}

    present_value = interface.calc_present_value(pool_state)
    idle_shares = interface.get_idle_shares(block_number)

    if not present_value >= idle_shares:
        difference_in_wei = abs(present_value.scaled_value - idle_shares.scaled_value)
        exception_message = f"{present_value=} < {idle_shares=}, {difference_in_wei=}"
        exception_data["invariance_check:idle_shares"] = idle_shares
        exception_data["invariance_check:current_present_value"] = present_value
        exception_data["invariance_check:present_value_difference_in_wei"] = difference_in_wei
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_lp_share_price(
    block_number: BlockNumber,
    interface: HyperdriveReadInterface,
    test_epsilon: float,
    pool_state: PoolState,
) -> InvariantCheckResults:
    """Returns True if the test (∆ lp_share_price > test_epsilon) fails.

    Arguments
    ---------
    block_number: BlockNumber
    interface: HyperdriveReadInterface
    test_epsilon: float
    pool_state: PoolState

    Returns
    -------
    InvariantCheckResults
    """
    # LP share price
    # for any trade, LP share price shouldn't change by more than 0.1%

    failed = False
    exception_message = ""
    exception_data: dict[str, Any] = {}

    # This is known to fail when checking the first block, as block - 1 doesn't exist.
    try:
        previous_pool_state = interface.get_hyperdrive_state(interface.get_block(block_number - 1))
    except BlockNotFound:
        return InvariantCheckResults(False, exception_message, exception_data)

    previous_lp_share_price = previous_pool_state.pool_info.lp_share_price
    current_lp_share_price = pool_state.pool_info.lp_share_price
    test_tolerance = previous_lp_share_price * FixedPoint(str(test_epsilon))

    if not fp_isclose(previous_lp_share_price, current_lp_share_price, abs_tol=test_tolerance):
        difference_in_wei = abs(previous_lp_share_price.scaled_value - current_lp_share_price.scaled_value)
        exception_message = f"{previous_lp_share_price=} != {current_lp_share_price=}, {difference_in_wei=}"
        exception_data["invariance_check:initial_lp_share_price"] = previous_lp_share_price
        exception_data["invariance_check:current_lp_share_price"] = current_lp_share_price
        exception_data["invariance_check:lp_share_price_difference_in_wei"] = difference_in_wei
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


class Args(NamedTuple):
    """Command line arguments for the invariant checker."""

    test_epsilon: float
    eth_config_env_file: str
    sleep_time: int


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
        eth_config_env_file=namespace.eth_config_env_file,
        sleep_time=namespace.sleep_time,
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
        help="The allowed error for equality tests.",
    )
    parser.add_argument(
        "--eth_config_env_file",
        type=str,
        default="eth.env",
        help="String pointing to eth config env file.",
    )
    parser.add_argument(
        "--sleep_time",
        type=int,
        default=5,
        help="Sleep time between checks, in seconds.",
    )

    # Use system arguments if none were passed
    if argv is None:
        argv = sys.argv

    return namespace_to_args(parser.parse_args())


if __name__ == "__main__":
    main()
