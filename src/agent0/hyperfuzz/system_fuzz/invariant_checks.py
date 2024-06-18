"""Runs invariant checks against a hyperdrive pool."""

from __future__ import annotations

import logging
from typing import Any, NamedTuple, Sequence

from fixedpointmath import FixedPoint, isclose
from hexbytes import HexBytes
from web3.exceptions import BlockNotFound
from web3.types import BlockData

from agent0.core.hyperdrive.crash_report import (
    build_crash_trade_result,
    get_anvil_state_dump,
    log_hyperdrive_crash_report,
)
from agent0.ethpy.hyperdrive import HyperdriveReadInterface
from agent0.ethpy.hyperdrive.state.pool_state import PoolState
from agent0.hyperfuzz import FuzzAssertionException

LP_SHARE_PRICE_EPSILON = 1e-4
TOTAL_SHARES_EPSILON = 1e-9


def run_invariant_checks(
    latest_block: BlockData,
    interface: HyperdriveReadInterface,
    raise_error_on_failure: bool = False,
    log_to_rollbar: bool = True,
    pool_name: str | None = None,
    lp_share_price_test: bool | None = None,
    crash_report_additional_info: dict[str, Any] | None = None,
) -> None:
    """Run the invariant checks.

    # Invariance checks (these should be True):
    - hyperdrive base & eth balances are zero
    - the expected total shares equals the hyperdrive balance in the vault contract
    - the pool has more than the minimum share reserves
    - the system is solvent, i.e. (share reserves - long exposure in shares - min share reserves) > 0
    - present value is greater than idle shares
    - the lp share price doesn't exceed an amount from block to block
    - if a hyperdrive trade happened then a checkpoint was created at the appropriate time
    - initializer's lp pnl should always be at or above the variable rate.

    Arguments
    ---------
    latest_block: BlockData
        The current block to be tested.
    interface: HyperdriveReadInterface
        An instantiated HyperdriveReadInterface object constructed using the script arguments.
    raise_error_on_failure: bool
        If True, raise an error if any invariant check fails.
    log_to_rollbar: bool
        If True, log to rollbar if any invariant check fails.
    pool_name: str | None
        The name of the pool for crash reporting information.
    lp_share_price_test: bool | None, optional
        If True, only test the lp share price. If False, skips the lp share price test.
        If None (default), runs all tests.
    crash_report_additional_info: dict[str, Any] | None
        Additional information to include in the crash report.
    """
    # TODO cleanup
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-arguments

    # Get the variables to check & check each invariant
    pool_state = interface.get_hyperdrive_state(latest_block)
    any_check_failed = False
    exception_message: list[str] = ["Continuous Fuzz Bots Invariant Checks"]
    exception_data: dict[str, Any] = {}
    if crash_report_additional_info is not None:
        exception_data.update(crash_report_additional_info)

    results: list[InvariantCheckResults]
    if lp_share_price_test is None:
        results = [
            _check_lp_share_price(interface, pool_state),
            _check_eth_balances(pool_state),
            _check_base_balances(pool_state, interface.base_is_eth),
            _check_total_shares(pool_state),
            _check_minimum_share_reserves(pool_state),
            _check_solvency(pool_state),
            _check_present_value_greater_than_idle_shares(interface, pool_state),
            _check_checkpointing_should_never_fail(interface, pool_state),
            _check_initial_lp_profitable(pool_state),
        ]
    else:
        if lp_share_price_test:
            results = [
                _check_lp_share_price(interface, pool_state),
            ]
        else:
            results = [
                _check_eth_balances(pool_state),
                _check_base_balances(pool_state, interface.base_is_eth),
                _check_total_shares(pool_state),
                _check_minimum_share_reserves(pool_state),
                _check_solvency(pool_state),
                _check_present_value_greater_than_idle_shares(interface, pool_state),
                _check_checkpointing_should_never_fail(interface, pool_state),
                _check_initial_lp_profitable(pool_state),
            ]

    for failed, message, data in results:
        any_check_failed = failed | any_check_failed
        if message:
            exception_message.append(message)
        exception_data.update(data)
        exception_data["block_number"] = pool_state.block_number

    # Log additional information if any test failed
    if any_check_failed:
        logging.critical("\n".join(exception_message))
        error = FuzzAssertionException(*exception_message, exception_data=exception_data)
        report = build_crash_trade_result(error, interface, additional_info=error.exception_data, pool_state=pool_state)
        report.anvil_state = get_anvil_state_dump(interface.web3)
        rollbar_data = error.exception_data

        if pool_name is not None:
            crash_report_file_prefix = "fuzz_bots_invariant_checks_" + pool_name
            rollbar_log_prefix = pool_name + "_"
        else:
            crash_report_file_prefix = "fuzz_bots_invariant_checks"
            rollbar_log_prefix = None

        log_hyperdrive_crash_report(
            report,
            crash_report_to_file=True,
            crash_report_file_prefix=crash_report_file_prefix,
            log_to_rollbar=log_to_rollbar,
            rollbar_data=rollbar_data,
            rollbar_log_prefix=rollbar_log_prefix,
        )
        if raise_error_on_failure:
            raise error


class InvariantCheckResults(NamedTuple):
    """Results from an invariant check."""

    failed: bool
    exception_message: str | None
    exception_data: dict[str, Any]


def _check_eth_balances(pool_state: PoolState) -> InvariantCheckResults:
    # Hyperdrive base & eth balances should always be zero
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}

    if pool_state.hyperdrive_eth_balance != FixedPoint(0):
        exception_message = f"{pool_state.hyperdrive_eth_balance} != 0."
        exception_data["invariance_check:actual_hyperdrive_eth_balance"] = pool_state.hyperdrive_eth_balance
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_base_balances(pool_state: PoolState, is_steth: bool) -> InvariantCheckResults:
    # Hyperdrive base & eth balances should always be zero
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}

    # We ignore this test for steth, as the base token here is actually the yield token
    if pool_state.hyperdrive_base_balance != FixedPoint(0) and not is_steth:
        exception_message = f"{pool_state.hyperdrive_base_balance} != 0."
        exception_data["invariance_check:actual_hyperdrive_base_balance"] = pool_state.hyperdrive_base_balance
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_checkpointing_should_never_fail(
    interface: HyperdriveReadInterface, pool_state: PoolState
) -> InvariantCheckResults:
    # Creating a checkpoint should never fail
    # TODO: add get_block_transactions() to interface
    # NOTE: This wold be prone to false positives.
    #   If the transaction would have failed anyway, then we don't know
    #   that it failed bc of checkpoint failure or bc e.g., open long was for too much
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}

    block = pool_state.block

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
            if txn_to == interface.hyperdrive_contract.address and pool_state.checkpoint.vault_share_price <= 0:
                exception_message = (
                    f"A transaction was created but no checkpoint was minted.\n"
                    f"{pool_state.checkpoint.vault_share_price=}\n"
                    f"{transaction=}\n"
                )
                failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_solvency(pool_state: PoolState) -> InvariantCheckResults:
    # The system should always be solvent
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}

    solvency = (
        pool_state.pool_info.share_reserves
        - pool_state.pool_info.long_exposure / pool_state.pool_info.vault_share_price
        - pool_state.pool_config.minimum_share_reserves
    )
    if solvency < FixedPoint(0):
        exception_message = (
            f"{solvency=} < 0. "
            f"({pool_state.pool_info.share_reserves=} - {pool_state.pool_info.long_exposure=} - "
            f"{pool_state.pool_config.minimum_share_reserves=})."
        )
        exception_data["invariance_check:solvency"] = solvency
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_minimum_share_reserves(pool_state: PoolState) -> InvariantCheckResults:
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
            f"{pool_state.pool_info.vault_share_price=} - "
            f"{pool_state.pool_info.long_exposure=})."
        )
        exception_data["invariance_check:current_share_reserves"] = current_share_reserves
        exception_data["invariance_check:minimum_share_reserves"] = minimum_share_reserves
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_total_shares(pool_state: PoolState) -> InvariantCheckResults:
    # Total shares is correctly calculated
    failed = False
    exception_message = ""
    exception_data: dict[str, Any] = {}

    expected_vault_shares = (
        pool_state.pool_info.share_reserves
        + (
            pool_state.pool_info.shorts_outstanding
            + (pool_state.pool_info.shorts_outstanding * pool_state.pool_config.fees.flat)
        )
        / pool_state.pool_info.vault_share_price
        + pool_state.gov_fees_accrued
        + pool_state.pool_info.withdrawal_shares_proceeds
        + pool_state.pool_info.zombie_share_reserves
    )
    actual_vault_shares = pool_state.vault_shares

    # While the expected vault shares is a bit inaccurate, we're testing
    # solvency here, hence, we ensure that the actual vault shares >= expected vault shares
    if actual_vault_shares < (expected_vault_shares - FixedPoint(str(TOTAL_SHARES_EPSILON))):
        difference_in_wei = abs(expected_vault_shares.scaled_value - actual_vault_shares.scaled_value)
        exception_message = (
            f"{actual_vault_shares=} is expected to be greater than {expected_vault_shares=}. {difference_in_wei=}. "
        )
        exception_data["invariance_check:expected_vault_shares"] = expected_vault_shares
        exception_data["invariance_check:actual_vault_shares"] = actual_vault_shares
        exception_data["invariance_check:vault_shares_difference_in_wei"] = difference_in_wei
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_present_value_greater_than_idle_shares(
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

    # Rust calls here can fail, we log if it does
    try:
        present_value = interface.calc_present_value(pool_state)
        idle_shares = interface.get_idle_shares(pool_state)
    # Catching rust panics here
    except BaseException as e:  # pylint: disable=broad-except
        return InvariantCheckResults(False, repr(e), exception_data)

    if not present_value >= idle_shares:
        difference_in_wei = abs(present_value.scaled_value - idle_shares.scaled_value)
        exception_message = f"{present_value=} < {idle_shares=}, {difference_in_wei=}"
        exception_data["invariance_check:idle_shares"] = idle_shares
        exception_data["invariance_check:current_present_value"] = present_value
        exception_data["invariance_check:present_value_difference_in_wei"] = difference_in_wei
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_lp_share_price(
    interface: HyperdriveReadInterface,
    pool_state: PoolState,
) -> InvariantCheckResults:
    """Returns True if the test (∆ lp_share_price > test_epsilon) fails."""
    # pylint: disable=too-many-locals

    # LP share price
    # for any trade, LP share price shouldn't change by more than 0.1%

    failed = False
    exception_message = ""
    exception_data: dict[str, Any] = {}

    block_number = pool_state.block_number

    # We expect the lp share price to be less than the test epsilon between sequential blocks
    # However, when simulating, we can advance time by any amount of time. Hence, we define
    # the test epsilon to be relative to 12 seconds (1 block), and normalize by the actual time
    # between blocks.

    # This is known to fail when checking the first block, as block - 1 doesn't exist.
    try:
        previous_pool_state = interface.get_hyperdrive_state(interface.get_block(block_number - 1))
    except BlockNotFound:
        return InvariantCheckResults(False, exception_message, exception_data)

    block_time_delta = pool_state.block_time - previous_pool_state.block_time
    normalized_test_epsilon = LP_SHARE_PRICE_EPSILON * (block_time_delta / 12)

    previous_lp_share_price = previous_pool_state.pool_info.lp_share_price
    current_lp_share_price = pool_state.pool_info.lp_share_price
    test_tolerance = previous_lp_share_price * FixedPoint(str(normalized_test_epsilon))

    # Relax check if
    # - a checkpoint was minted on the current block
    # - closing mature position this block

    # Determine if a checkpoint was minted on the current block
    # -1 to get events from current block
    checkpoint_events = interface.hyperdrive_contract.events.CreateCheckpoint.get_logs(
        fromBlock=pool_state.block_number - 1
    )
    currently_minting_checkpoint = False
    if len(list(checkpoint_events)) > 0:
        currently_minting_checkpoint = True

    # Determine if matured positions were closed this timestamp
    # We look for close events on this block
    # -1 to get events from current block
    trade_events = []
    trade_events.extend(interface.hyperdrive_contract.events.CloseShort.get_logs(fromBlock=pool_state.block_number - 1))
    trade_events.extend(interface.hyperdrive_contract.events.CloseLong.get_logs(fromBlock=pool_state.block_number - 1))

    closing_mature_position = False
    for event in trade_events:
        # maturityTime should always be part of close short/long
        assert "maturityTime" in event.args
        # Race condition, filter only on events from the current block
        # Check if any matured positions were closed
        if (event.blockNumber == pool_state.block_number) and (pool_state.block_time >= event.args.maturityTime):
            closing_mature_position = True
            break

    # Full check
    if not currently_minting_checkpoint and not closing_mature_position:
        if not isclose(previous_lp_share_price, current_lp_share_price, abs_tol=test_tolerance):
            failed = True
    # Relaxed check
    else:
        if (previous_lp_share_price - current_lp_share_price) >= test_tolerance:
            failed = True

    if failed:
        difference_in_wei = abs(previous_lp_share_price.scaled_value - current_lp_share_price.scaled_value)
        exception_message = f"{previous_lp_share_price=} != {current_lp_share_price=}, {difference_in_wei=}"
        exception_data["invariance_check:initial_lp_share_price"] = previous_lp_share_price
        exception_data["invariance_check:current_lp_share_price"] = current_lp_share_price
        exception_data["invariance_check:lp_share_price_difference_in_wei"] = difference_in_wei
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)


def _check_initial_lp_profitable(pool_state: PoolState, epsilon: FixedPoint | None = None) -> InvariantCheckResults:

    if epsilon is None:
        epsilon = FixedPoint("0.005")

    failed = False
    exception_message = ""
    exception_data: dict[str, Any] = {}

    # We compare the rate of lp share price vs the rate of vault share price
    # For this, we need to get the initial and current prices of both
    initial_vault_share_price = pool_state.pool_config.initial_vault_share_price
    current_vault_share_price = pool_state.pool_info.vault_share_price

    # LP Share price is always 1 at initialization
    initial_lp_share_price = FixedPoint(1)
    current_lp_share_price = pool_state.pool_info.lp_share_price

    # We calculate both rates and compare
    # The rate calculated here is for the time range of how long the pool has deployed
    vault_rate = (current_vault_share_price - initial_vault_share_price) / initial_vault_share_price
    lp_rate = (current_lp_share_price - initial_lp_share_price) / initial_lp_share_price

    difference_in_wei = lp_rate.scaled_value - vault_rate.scaled_value

    if difference_in_wei < (-epsilon.scaled_value):
        exception_message = f"{lp_rate=} is expected to be >= {vault_rate=}, {difference_in_wei=}"
        exception_data["invariance_check:lp_rate"] = lp_rate
        exception_data["invariance_check:vault_rate"] = vault_rate
        exception_data["invariance_check:lp_vault_rate_difference_in_wei"] = difference_in_wei
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data)
