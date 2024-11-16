"""Runs invariant checks against a hyperdrive pool."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Callable, NamedTuple

from fixedpointmath import FixedPoint
from hyperdrivetypes.types.IHyperdrive import CloseLongEvent, CloseShortEvent
from web3.types import BlockData

from agent0.core.hyperdrive.crash_report import (
    build_crash_trade_result,
    get_anvil_state_dump,
    log_hyperdrive_crash_report,
)
from agent0.ethpy.hyperdrive import HyperdriveReadInterface
from agent0.ethpy.hyperdrive.state.pool_state import PoolState
from agent0.hyperfuzz import FuzzAssertionException
from agent0.utils import block_number_before_timestamp

LP_SHARE_PRICE_EPSILON = 1e-4
TOTAL_SHARES_EPSILON = 1e-9
NEGATIVE_INTEREST_ATOL = FixedPoint(scaled_value=10)  # absolute tolerance 10 wei
NEGATIVE_INTEREST_RTOL = FixedPoint(0.001)  # relative tolerance 10bp
PRESENT_VALUE_EPSILON = FixedPoint(scaled_value=1)  # 1 wei
EZETH_NEG_INTEREST_TIME_DELTA = 12 * 60 * 60


def run_invariant_checks(
    check_block_data: BlockData,
    interface: HyperdriveReadInterface,
    log_to_rollbar: bool = True,
    rollbar_log_level_threshold: int | None = None,
    rollbar_log_filter_func: Callable[[Exception], bool] | None = None,
    pool_name: str | None = None,
    lp_share_price_test: bool | None = None,
    crash_report_additional_info: dict[str, Any] | None = None,
    log_anvil_state_dump: bool = False,
    pending_pool_state: PoolState | None = None,
    check_price_spike: bool = True,
) -> list[FuzzAssertionException]:
    """Run the invariant checks.

    # Invariance checks (these should be True):
    - hyperdrive base & eth balances are zero
    - the expected total shares equals the hyperdrive balance in the vault contract
    - the pool has more than the minimum share reserves
    - the system is solvent, i.e. (share reserves - long exposure in shares - min share reserves) > 0
    - present value is greater than idle shares
    - the lp share price doesn't exceed an amount from block to block
    - check negative interest on yield source
    - Warn if a trade causes a large rate spike; which is a precursor to an attack

    Arguments
    ---------
    check_block_data: BlockData
        The current block to be tested.
    interface: HyperdriveReadInterface
        An instantiated HyperdriveReadInterface object constructed using the script arguments.
    log_to_rollbar: bool
        If True, log to rollbar if any invariant check fails.
    rollbar_log_level_threshold: int | None, optional
        Threshold for logging to rollbar.
    rollbar_log_filter_func: Callable[[Exception], bool] | None
        A function that filters exceptions to log to rollbar. The function should return
        `True` for exceptions that should be filtered from rollbar logging.
        Defaults to logging all exceptions.
    pool_name: str | None
        The name of the pool for crash reporting information.
    lp_share_price_test: bool | None, optional
        If True, only test the lp share price. If False, skips the lp share price test.
        If None (default), runs all tests.
    crash_report_additional_info: dict[str, Any] | None
        Additional information to include in the crash report.
    log_anvil_state_dump: bool
        If True, log anvil state dump on crash.
    pending_pool_state: BlockData | None, optional
        The pool state for the pending block. If None, assumes the block is ticking in the
        background and will maintain the pending block itself.
    check_price_spike: bool
        If True, check price spike

    Returns
    -------
    list[FuzzAssertionException]
        A list of FuzzAssertionExceptions, one for each failed invariant check.
    """
    # TODO cleanup
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-arguments
    # pylint: disable=too-many-positional-arguments
    # pylint: disable=too-many-branches

    logging.info("Running invariant checks on pool %s", pool_name)

    if rollbar_log_level_threshold is None:
        rollbar_log_level_threshold = logging.DEBUG

    # Get the variables to check & check each invariant
    pool_state = interface.get_hyperdrive_state(block_data=check_block_data)

    results: list[InvariantCheckResults]
    if lp_share_price_test is None:
        # Available log levels:
        # Critical (pager duty)
        # Error (not pager duty, important)
        # Warning (not pager duty, may be important)
        # Info (not important)

        results = [
            # Critical if lp share price is down,
            # Warn if lp share price is up
            _check_lp_share_price(interface, pending_pool_state=pending_pool_state),
            # Warning
            _check_eth_balances(pool_state),
            # Info
            _check_base_balances(pool_state, interface.base_is_yield),
            # Critical (after diving down into steth failure)
            _check_total_shares(interface, pool_state),
            # Critical
            _check_minimum_share_reserves(pool_state),
            # Critical
            _check_solvency(pool_state),
            # Critical
            _check_present_value_greater_than_idle_shares(interface, pool_state),
            # Error
            _check_negative_interest(interface, pool_state),
            # TODO
            # If at any point, we can open a long to make share price to 1
            # Get spot price after long
        ]
        if check_price_spike:
            # Warning
            results.append(_check_price_spike(interface, pool_state))

    else:
        if lp_share_price_test:
            results = [
                _check_lp_share_price(interface, pending_pool_state=pending_pool_state),
            ]
        else:
            results = [
                _check_eth_balances(pool_state),
                _check_base_balances(pool_state, interface.base_is_yield),
                _check_total_shares(interface, pool_state),
                _check_minimum_share_reserves(pool_state),
                _check_solvency(pool_state),
                _check_present_value_greater_than_idle_shares(interface, pool_state),
                _check_negative_interest(interface, pool_state),
            ]
            if check_price_spike:
                # Warning
                results.append(_check_price_spike(interface, pool_state))

    exception_message_base = ["Continuous Fuzz Bots Invariant Checks"]
    exception_data_template: dict[str, Any] = {}
    if crash_report_additional_info is not None:
        exception_data_template.update(crash_report_additional_info)

    out_exceptions: list[FuzzAssertionException] = []
    for failed, message, data, log_level in results:
        if not failed:
            continue
        exception_message = exception_message_base.copy()
        if message:
            exception_message.append(message)
        exception_data = exception_data_template.copy()
        exception_data.update(data)
        exception_data["block_number"] = pool_state.block_number
        exception_data["pool_name"] = pool_name

        # Log exception to rollbar
        assert log_level is not None
        logging.log(log_level, "\n".join(exception_message))
        error = FuzzAssertionException(*exception_message, exception_data=exception_data)
        out_exceptions.append(error)
        report = build_crash_trade_result(error, interface, additional_info=error.exception_data, pool_state=pool_state)
        if log_anvil_state_dump:
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
            log_level=log_level,
            crash_report_stdout_summary=False,
            crash_report_to_file=True,
            crash_report_file_prefix=crash_report_file_prefix,
            log_to_rollbar=log_to_rollbar,
            rollbar_log_level_threshold=rollbar_log_level_threshold,
            rollbar_log_prefix=rollbar_log_prefix,
            rollbar_data=rollbar_data,
            rollbar_log_filter_func=rollbar_log_filter_func,
        )
    return out_exceptions


class InvariantCheckResults(NamedTuple):
    """Results from an invariant check."""

    failed: bool
    exception_message: str | None
    exception_data: dict[str, Any]
    log_level: int | None


def _check_price_spike(interface: HyperdriveReadInterface, pool_state: PoolState) -> InvariantCheckResults:
    # Warn if a trade causes a large rate spike; which is a precursor to an attack
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}
    log_level = None
    delta_rate_epsilon = interface.pool_config.circuit_breaker_delta

    # TODO we hack in a stateful variable into the interface here to check
    # between subsequent calls.
    # Initial call, we look to see if the attribute exists
    previous_pool_state: PoolState | None = getattr(interface, "_price_spike_previous_pool_state", None)
    # Always set the new state here
    setattr(interface, "_price_spike_previous_pool_state", pool_state)

    if previous_pool_state is None:
        # Skip this check on initial call, not a failure
        return InvariantCheckResults(
            failed=False, exception_message=exception_message, exception_data=exception_data, log_level=log_level
        )

    if previous_pool_state.checkpoint.weighted_spot_price == FixedPoint(0):
        # Skip this if the weighted spot price is 0
        # TODO: Is this the right thing to do?
        return InvariantCheckResults(
            failed=False, exception_message=exception_message, exception_data=exception_data, log_level=log_level
        )

    # The checkpoint weighted spot price is updated every checkpoint and every trade.
    previous_weighted_spot_rate = interface.calc_rate_given_fixed_price(
        previous_pool_state.checkpoint.weighted_spot_price,
        FixedPoint(scaled_value=previous_pool_state.pool_config.position_duration),
    )

    current_spot_price = interface.calc_spot_price(pool_state)
    if current_spot_price == FixedPoint(0):
        # Skip this if the weighted spot price is 0
        # TODO: Is this the right thing to do?
        return InvariantCheckResults(
            failed=False, exception_message=exception_message, exception_data=exception_data, log_level=log_level
        )

    current_spot_rate = interface.calc_rate_given_fixed_price(
        current_spot_price,
        FixedPoint(scaled_value=previous_pool_state.pool_config.position_duration),
    )

    if abs(current_spot_rate - previous_weighted_spot_rate) >= delta_rate_epsilon:
        exception_data["invariance_check:current_spot_rate"] = current_spot_rate
        exception_data["invariance_check:previous_weighted_spot_rate"] = previous_weighted_spot_rate
        exception_data["invariance_check:current_spot_price"] = current_spot_price
        exception_data["invariance_check:previous_weighted_spot_price"] = (
            previous_pool_state.checkpoint.weighted_spot_price
        )
        failed = True
        exception_message = (
            "Large trade has caused the rate circuit breaker to trip. "
            f"{current_spot_rate=}, {previous_weighted_spot_rate=}. "
            "Difference: "
            f"{current_spot_rate- previous_weighted_spot_rate}."
        )
        log_level = logging.WARNING

    return InvariantCheckResults(failed, exception_message, exception_data, log_level=log_level)


def _check_negative_interest(interface: HyperdriveReadInterface, pool_state: PoolState) -> InvariantCheckResults:
    """Check for negative interest in the pool.

    If the rate went down, post a log
    If the pool is paused, log is warning regardless of relative rate change
    If the pool is not paused and the rate went down by more than the relative tol, log is critical
    If the pool is not paused, but the rate did not go down by more than the relative tol, log is warning
    """
    # Hyperdrive base & eth balances should always be zero
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}
    log_level = None

    current_block_time = pool_state.block_time
    current_vault_share_price = pool_state.pool_info.vault_share_price

    deploy_block = interface.get_deploy_block_number()
    if deploy_block is None:  # type narrowing
        raise ValueError("Deploy block not found.")
    deploy_block_time = interface.get_block_timestamp(interface.get_block(deploy_block))
    if interface.hyperdrive_name == "ElementDAO 182 Day ezETH Hyperdrive":
        lookback_timestamp = current_block_time - 60 * 60 * 12  # 12 hours ago
    else:
        lookback_timestamp = current_block_time - 60 * 60 * 1  # 1 hour ago
    if lookback_timestamp < deploy_block_time:
        previous_block_number = deploy_block
    else:
        previous_block_number = block_number_before_timestamp(interface.web3, lookback_timestamp)
    previous_pool_state = interface.get_hyperdrive_state(block_identifier=previous_block_number)
    previous_vault_share_price = previous_pool_state.pool_info.vault_share_price

    # Absolute check to see if the rate went down
    if current_vault_share_price - previous_vault_share_price <= -NEGATIVE_INTEREST_ATOL:
        log_level = logging.WARNING
        if interface.get_pool_is_paused():
            paused_str = "paused"
        else:
            paused_str = "unpaused"
            # relative check to see if the rate went down by a lot
            if previous_vault_share_price * (FixedPoint(1) - NEGATIVE_INTEREST_RTOL) >= current_vault_share_price:
                log_level = logging.CRITICAL
        failed = True
        exception_data["invariance_check:current_vault_share_price"] = current_vault_share_price
        exception_data["invariance_check:previous_vault_share_price"] = previous_vault_share_price
        exception_message = (
            "Negative interest detected beteween block "
            f"{previous_pool_state.block_number} "
            "at time "
            f"{datetime.fromtimestamp(previous_pool_state.block_time).strftime('%Y-%m-%d %H:%M:%S')}"
            "and block "
            f"{pool_state.block_number} "
            "at time "
            f"{datetime.fromtimestamp(pool_state.block_time).strftime('%Y-%m-%d %H:%M:%S')}"
            f"on {paused_str} pool. "
            f"{current_vault_share_price=}, {previous_vault_share_price=}. "
            "Difference in wei: "
            f"{current_vault_share_price.scaled_value - previous_vault_share_price.scaled_value}."
        )

    return InvariantCheckResults(failed, exception_message, exception_data, log_level=log_level)


def _check_eth_balances(pool_state: PoolState) -> InvariantCheckResults:
    # Hyperdrive base & eth balances should always be zero
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}
    log_level = None

    if pool_state.hyperdrive_eth_balance != FixedPoint(0):
        exception_message = f"Pool eth balance {pool_state.hyperdrive_eth_balance} != 0."
        exception_data["invariance_check:actual_hyperdrive_eth_balance"] = pool_state.hyperdrive_eth_balance
        failed = True
        log_level = logging.WARNING

    return InvariantCheckResults(failed, exception_message, exception_data, log_level=log_level)


def _check_base_balances(pool_state: PoolState, base_is_yield: bool) -> InvariantCheckResults:
    # Hyperdrive base & eth balances should always be zero
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}
    log_level = None

    # We ignore this test for steth, as the base token here is actually the yield token
    if pool_state.hyperdrive_base_balance != FixedPoint(0) and not base_is_yield:
        exception_message = f"Pool base balance {pool_state.hyperdrive_base_balance} != 0."
        exception_data["invariance_check:actual_hyperdrive_base_balance"] = pool_state.hyperdrive_base_balance
        failed = True
        log_level = logging.INFO

    return InvariantCheckResults(failed, exception_message, exception_data, log_level=log_level)


def _check_solvency(pool_state: PoolState) -> InvariantCheckResults:
    # The system should always be solvent
    failed = False
    exception_message: str | None = None
    exception_data: dict[str, Any] = {}
    log_level = None

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
        log_level = logging.CRITICAL

    return InvariantCheckResults(failed, exception_message, exception_data, log_level)


def _check_minimum_share_reserves(pool_state: PoolState) -> InvariantCheckResults:
    # The pool has more than the minimum share reserves
    failed = False
    exception_message = ""
    exception_data: dict[str, Any] = {}
    log_level = logging.CRITICAL

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

    return InvariantCheckResults(failed, exception_message, exception_data, log_level=log_level)


def _check_total_shares(interface: HyperdriveReadInterface, pool_state: PoolState) -> InvariantCheckResults:
    # Total shares is correctly calculated
    failed = False
    exception_message = ""
    exception_data: dict[str, Any] = {}
    log_level = None

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

    # We use a slightly bigger tolerance for the wsteth-usda pool
    if interface.hyperdrive_name == "ElementDAO 182 Day Morpho Blue wstETH/USDA Hyperdrive":
        shares_epsilon = 1e-5
    else:
        shares_epsilon = TOTAL_SHARES_EPSILON

    # While the expected vault shares is a bit inaccurate, we're testing
    # solvency here, hence, we ensure that the actual vault shares >= expected vault shares
    if actual_vault_shares < (expected_vault_shares - FixedPoint(str(shares_epsilon))):
        difference_in_wei = abs(expected_vault_shares.scaled_value - actual_vault_shares.scaled_value)
        exception_message = (
            f"{actual_vault_shares=} is expected to be greater than {expected_vault_shares=}. {difference_in_wei=}. "
        )
        exception_data["invariance_check:expected_vault_shares"] = expected_vault_shares
        exception_data["invariance_check:actual_vault_shares"] = actual_vault_shares
        exception_data["invariance_check:vault_shares_difference_in_wei"] = difference_in_wei
        failed = True
        log_level = logging.CRITICAL

    return InvariantCheckResults(failed, exception_message, exception_data, log_level)


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
    log_level = None

    # Rust calls here can fail, we log if it does
    try:
        present_value = interface.calc_present_value(pool_state)
        idle_shares = interface.get_idle_shares(pool_state)
    # Catching rust panics here
    except BaseException as e:  # pylint: disable=broad-except
        return InvariantCheckResults(
            failed=True, exception_message=repr(e), exception_data=exception_data, log_level=logging.CRITICAL
        )

    if not present_value >= (idle_shares - PRESENT_VALUE_EPSILON):
        difference_in_wei = abs(present_value.scaled_value - idle_shares.scaled_value)
        exception_message = f"{present_value=} < {idle_shares=}, {difference_in_wei=}"
        exception_data["invariance_check:idle_shares"] = idle_shares
        exception_data["invariance_check:current_present_value"] = present_value
        exception_data["invariance_check:present_value_difference_in_wei"] = difference_in_wei
        failed = True
        log_level = logging.CRITICAL

    return InvariantCheckResults(failed, exception_message, exception_data, log_level)


def _check_lp_share_price(
    interface: HyperdriveReadInterface, pending_pool_state: PoolState | None
) -> InvariantCheckResults:
    """Returns True if the test (∆ lp_share_price > test_epsilon) fails."""
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-statements
    # pylint: disable=too-many-branches

    # LP share price
    # for any trade, LP share price shouldn't change by more than 0.1%

    failed = False
    exception_message = ""
    exception_data: dict[str, Any] = {}
    log_level = None

    # If a pending pool state isn't passed in, we maintain it ourself
    if pending_pool_state is None:
        # TODO we hack in a stateful variable into the interface here, since we need
        # to check between subsequent calls here.
        # Initial call, we look to see if the attribute exists
        _pending_pool_state: PoolState | None = getattr(interface, "_lp_share_price_check_state", None)
        # Always set the new pending state here
        setattr(interface, "_lp_share_price_check_state", interface.get_hyperdrive_state("pending"))

        if _pending_pool_state is None:
            # Skip this check on initial call, not a failure
            return InvariantCheckResults(
                failed=False, exception_message=exception_message, exception_data=exception_data, log_level=log_level
            )
    # Otherwise, we use the one passed in.
    else:
        _pending_pool_state = pending_pool_state

    # This is the block we're checking the lp share price on
    check_block_number = _pending_pool_state.block_number

    # There's a chance this check gets called again before the check_block_number has been mined.
    # Hence, we ensure that the check_block_number has been mined before making the check
    loop_counter = 0
    while True:
        if loop_counter > 24:
            raise AssertionError("Check block number has not been mined in a reasonable amount of time")
        curr_block = interface.get_block_number(interface.get_current_block())
        if curr_block < check_block_number:
            loop_counter += 1
            time.sleep(1)
        else:
            break

    # Get the pool state after it was mined
    mined_pool_state = interface.get_hyperdrive_state(block_data=interface.get_block(check_block_number))

    pending_lp_share_price = _pending_pool_state.pool_info.lp_share_price
    mined_lp_share_price = mined_pool_state.pool_info.lp_share_price

    test_tolerance = pending_lp_share_price * FixedPoint(str(LP_SHARE_PRICE_EPSILON))

    # Relax check if
    # - a checkpoint was minted on the current block
    # - closing mature position this block

    # Determine if a checkpoint was minted on the current block
    # -1 to get events from current block
    checkpoint_events = interface.hyperdrive_contract.events.CreateCheckpoint.get_logs_typed(
        from_block=check_block_number - 1
    )
    currently_minting_checkpoint = False
    for event in checkpoint_events:
        if event.block_number == check_block_number:
            currently_minting_checkpoint = True
            break

    # Determine if matured positions were closed this timestamp
    # We look for close events on this block
    # -1 to get events from current block
    trade_events: list[CloseShortEvent | CloseLongEvent] = []
    trade_events.extend(
        interface.hyperdrive_contract.events.CloseShort.get_logs_typed(from_block=check_block_number - 1)
    )
    trade_events.extend(
        interface.hyperdrive_contract.events.CloseLong.get_logs_typed(from_block=check_block_number - 1)
    )

    closing_mature_position = False
    for event in trade_events:
        # Race condition, filter only on events from the current block
        # Check if any matured positions were closed
        if (event.block_number == check_block_number) and (mined_pool_state.block_time >= event.args.maturityTime):
            closing_mature_position = True
            break

    # We check if lp share price jumps higher than expected
    # if we're doing a full check. In this case, we warn
    difference_in_wei = abs(pending_lp_share_price.scaled_value - mined_lp_share_price.scaled_value)
    if not currently_minting_checkpoint and not closing_mature_position:
        if (mined_lp_share_price - pending_lp_share_price) >= test_tolerance:
            failed = True
            exception_message = (
                f"LP share price went up more than expected on block {check_block_number}: "
                f"{pending_lp_share_price=}, {mined_lp_share_price=}, {difference_in_wei=}"
            )
            log_level = logging.WARNING

    # We always check if lp share price jumps lower than expected.
    # In this case, we throw critical.
    if (pending_lp_share_price - mined_lp_share_price) >= test_tolerance:
        failed = True
        exception_message = (
            f"LP share price went down more than expected on block {check_block_number}: "
            f"{pending_lp_share_price=}, {mined_lp_share_price=}, {difference_in_wei=}"
        )
        log_level = logging.CRITICAL

    if failed:
        exception_data["invariance_check:pending_lp_share_price"] = pending_lp_share_price
        exception_data["invariance_check:mined_lp_share_price"] = mined_lp_share_price
        exception_data["invariance_check:lp_share_price_difference_in_wei"] = difference_in_wei
        failed = True

    return InvariantCheckResults(failed, exception_message, exception_data, log_level)
