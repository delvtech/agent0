"""Helper functions for checking for known errors in contract calls."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from fixedpointmath import FixedPoint
from web3.exceptions import ContractCustomError

from agent0.core.hyperdrive.agent import HyperdriveActionType
from agent0.core.test_utils import assert_never
from agent0.ethpy.base.errors import ContractCallException
from agent0.ethpy.hyperdrive import HyperdriveReadInterface

if TYPE_CHECKING:
    from agent0.core.hyperdrive import TradeResult


# pylint: disable=too-many-statements
def check_for_invalid_balance(trade_result: TradeResult, interface: HyperdriveReadInterface) -> TradeResult:
    """Detects invalid balance errors in trade_result and adds additional information to the
    exception in trade_result.

    Arguments
    ---------
    trade_result: TradeResult
        The trade result object from trading.
    interface: HyperdriveReadInterface
        The hyperdrive read interface to compute expected balances for trades.

    Returns
    -------
    TradeResult
        A modified trade_result that has a custom exception argument message prepended
    """
    assert trade_result.wallet is not None
    wallet = trade_result.wallet
    assert trade_result.trade_object is not None
    trade_type = trade_result.trade_object.market_action.action_type
    trade_amount = trade_result.trade_object.market_action.trade_amount
    maturity_time = trade_result.trade_object.market_action.maturity_time
    invalid_balance = False
    add_arg = None
    match trade_type:
        case HyperdriveActionType.INITIALIZE_MARKET:
            raise ValueError(f"{trade_type} not supported!")

        case HyperdriveActionType.OPEN_LONG:
            if trade_amount > wallet.balance.amount:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} {wallet.balance.unit.name}, "
                    f"balance of {wallet.balance.amount} {wallet.balance.unit.name}."
                )

        case HyperdriveActionType.CLOSE_LONG:
            # Long doesn't exist
            if maturity_time not in wallet.longs:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} long-{maturity_time}, "
                    f"long token not found in wallet."
                )
            # Long exists but not enough balance
            else:
                if trade_amount > wallet.longs[maturity_time].balance:
                    invalid_balance = True
                    add_arg = (
                        f"Invalid balance: {trade_type.name} for {trade_amount} long-{maturity_time}, "
                        f"balance of {wallet.longs[maturity_time].balance} long-{maturity_time}."
                    )

        case HyperdriveActionType.OPEN_SHORT:
            # We use the interface to calculate the amount of deposit required to open
            # the provided short.
            # TODO there may be a race condition here if the block ticks while handling this crash

            # We catch all errors thrown by calc open short in rust. If the underlying function
            # fails, it's likely not an invalid balance issue.
            base_deposit = None
            try:
                base_deposit = interface.calc_open_short(trade_amount)
            except BaseException:  # pylint: disable=broad-except
                pass

            if base_deposit is not None and base_deposit > wallet.balance.amount:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} bonds, "
                    f"expected deposit of {base_deposit} {wallet.balance.unit.name}, "
                    f"balance of {wallet.balance.amount} {wallet.balance.unit.name}."
                )

        case HyperdriveActionType.CLOSE_SHORT:
            # Short doesn't exist
            if maturity_time not in wallet.shorts:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} short-{maturity_time}, "
                    f"short token not found in wallet."
                )
            # Short exists but not enough balance
            else:
                if trade_amount > wallet.shorts[maturity_time].balance:
                    invalid_balance = True
                    add_arg = (
                        f"Invalid balance: {trade_type.name} for {trade_amount} short-{maturity_time}, "
                        f"balance of {wallet.shorts[maturity_time].balance} short-{maturity_time}."
                    )

        case HyperdriveActionType.ADD_LIQUIDITY:
            if trade_amount > wallet.balance.amount:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} {wallet.balance.unit.name}, "
                    f"balance of {wallet.balance.amount} {wallet.balance.unit.name}."
                )

        case HyperdriveActionType.REMOVE_LIQUIDITY:
            if trade_amount > wallet.lp_tokens:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} LP tokens, "
                    f"balance of {wallet.lp_tokens} LP tokens."
                )

        case HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
            # If we're crash reporting, pool_info should exist
            assert trade_result.pool_info is not None
            ready_to_withdraw = trade_result.pool_info["withdrawal_shares_ready_to_withdraw"]
            if trade_amount > wallet.withdraw_shares:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} withdraw shares, "
                    f"balance of {wallet.withdraw_shares} withdraw shares."
                )
            # Also checking that there are enough withdrawal shares ready to withdraw
            elif trade_amount > ready_to_withdraw:
                invalid_balance = True
                add_arg = (
                    f"Invalid balance: {trade_type.name} for {trade_amount} withdraw shares, "
                    f"not enough ready to withdraw shares in pool ({ready_to_withdraw})."
                )

        case _:
            assert_never(trade_type)

    # Prepend balance error argument to exception args
    if invalid_balance:
        assert trade_result.exception is not None
        assert add_arg is not None
        trade_result.exception.args = (add_arg,) + trade_result.exception.args
        trade_result.is_invalid_balance = True

    return trade_result


def check_for_insufficient_allowance(trade_result: TradeResult, interface: HyperdriveReadInterface) -> TradeResult:
    """Detects insufficient allowance in trade_result and adds additional information to the
    exception in trade_result.

    Arguments
    ---------
    trade_result: TradeResult
        The trade result object from trading.
    interface: HyperdriveReadInterface
        The hyperdrive read interface to compute expected balances for trades.

    Returns
    -------
    TradeResult
        A modified trade_result that has a custom exception argument message prepended.
    """
    assert trade_result.account is not None
    agent_address = trade_result.account.address
    assert trade_result.trade_object is not None
    trade_type = trade_result.trade_object.market_action.action_type
    trade_amount = trade_result.trade_object.market_action.trade_amount

    base_token_contract_address = interface.base_token_contract.address
    hyperdrive_contract_address = interface.hyperdrive_contract.address

    insufficient_allowance = False
    add_arg = None
    match trade_type:
        case HyperdriveActionType.INITIALIZE_MARKET:
            raise ValueError(f"{trade_type} not supported!")

        case HyperdriveActionType.ADD_LIQUIDITY | HyperdriveActionType.OPEN_LONG:
            allowance = None
            try:
                allowance = FixedPoint(
                    scaled_value=interface.base_token_contract.functions.allowance(
                        agent_address,
                        hyperdrive_contract_address,
                    ).call()
                )
            except Exception as e:  # pylint: disable=broad-except
                logging.warning("Failed to get allowance in crash reporting: %s", e)

            if allowance is not None and allowance < trade_amount:
                insufficient_allowance = True
                add_arg = (
                    f"Insufficient allowance: {trade_type.name} for {trade_amount} , "
                    f"allowance of {allowance} for token {base_token_contract_address}."
                )

        case HyperdriveActionType.OPEN_SHORT:
            allowance = None
            try:
                allowance = FixedPoint(
                    scaled_value=interface.base_token_contract.functions.allowance(
                        agent_address,
                        hyperdrive_contract_address,
                    ).call()
                )
            except Exception as e:  # pylint: disable=broad-except
                logging.warning("Failed to get allowance in crash reporting: %s", e)

            # Since the trade amount here is in units of bonds, we only check for
            # 0 allowance here.
            # TODO calculate short deposit value here
            if allowance is not None and allowance == 0:
                insufficient_allowance = True
                add_arg = (
                    f"Insufficient allowance: {trade_type.name} for {trade_amount} , "
                    f"allowance of {allowance} for token {base_token_contract_address}."
                )

        case (
            HyperdriveActionType.REMOVE_LIQUIDITY
            | HyperdriveActionType.CLOSE_LONG
            | HyperdriveActionType.CLOSE_SHORT
            | HyperdriveActionType.REDEEM_WITHDRAW_SHARE
        ):
            # No need for approval for close trades
            pass

        case _:
            assert_never(trade_type)

    # Prepend balance error argument to exception args
    if insufficient_allowance:
        assert trade_result.exception is not None
        assert add_arg is not None
        trade_result.exception.args = (add_arg,) + trade_result.exception.args
        trade_result.is_insufficient_allowance = True

    return trade_result


def check_for_slippage(trade_result: TradeResult) -> TradeResult:
    """Detects slippage errors in trade_result and adds additional information to the
    exception in trade_result

    Arguments
    ---------
    trade_result: TradeResult
        The trade result object from trading

    Returns
    -------
    TradeResult
        A modified trade_result that has a custom exception argument message prepended
    """
    # To detect slippage, we first look for the wrapper that defines a contract call exception.
    # We then look for the `OutputLimit` exception thrown as the original exception.
    # Since this exception is used elsewhere (e.g., in redeem withdraw shares), we also explicitly check
    # that the trade here is open/close long/short.
    # TODO this error is not guaranteed to be exclusive for slippage in the future.
    assert trade_result.trade_object is not None
    is_slippage = (
        isinstance(trade_result.exception, ContractCallException)
        and isinstance(trade_result.exception.orig_exception, ContractCustomError)
        and ("OutputLimit raised" in trade_result.exception.orig_exception.args[1])
        and (
            trade_result.trade_object.market_action.action_type
            in (
                HyperdriveActionType.OPEN_LONG,
                HyperdriveActionType.CLOSE_LONG,
                HyperdriveActionType.OPEN_SHORT,
                HyperdriveActionType.CLOSE_SHORT,
            )
        )
    )
    if is_slippage:
        assert trade_result.exception is not None
        # Prepend slippage argument to exception args
        trade_result.exception.args = ("Slippage detected",) + trade_result.exception.args
        trade_result.is_slippage = True

    return trade_result


def check_for_min_txn_amount(trade_result: TradeResult) -> TradeResult:
    """Detects minimum transaction amount errors in trade_result and adds additional information to the
    exception in trade_result

    Arguments
    ---------
    trade_result: TradeResult
        The trade result object from trading

    Returns
    -------
    TradeResult
        A modified trade_result that has a custom exception argument message prepended
    """

    assert trade_result.pool_config is not None
    assert trade_result.trade_object is not None

    trade_type = trade_result.trade_object.market_action.action_type
    add_arg = None
    is_min_txn_amount = False

    # Redeem withdrawal shares is not subject to minimum transaction amounts
    if trade_type != HyperdriveActionType.REDEEM_WITHDRAW_SHARE:
        min_txn_amount = trade_result.pool_config["minimum_transaction_amount"]
        trade_amount = trade_result.trade_object.market_action.trade_amount
        if trade_amount < min_txn_amount:
            add_arg = (
                f"Minimum Transaction Amount: {trade_type.name} for {trade_amount}, "
                f"minimum transaction amount is {min_txn_amount}."
            )
            is_min_txn_amount = True

    # Prepend balance error argument to exception args
    if is_min_txn_amount:
        assert add_arg is not None
        assert trade_result.exception is not None
        trade_result.exception.args = (add_arg,) + trade_result.exception.args
        trade_result.is_min_txn_amount = True

    return trade_result
