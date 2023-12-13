"""Calculates the pnl."""
from __future__ import annotations

import logging
from decimal import Decimal
from ethpy.hyperdrive.interface.interface import HyperdriveInterface
from ethpy.hyperdrive.state.pool_state import PoolState

import pandas as pd
from eth_typing import ChecksumAddress, HexAddress, HexStr
from ethpy.base import smart_contract_preview_transaction
from ethpy.hyperdrive import BASE_TOKEN_SYMBOL
from fixedpointmath import FixedPoint
from web3.contract.contract import Contract


def calculate_close_long_flat_plus_curve(
    amount_bonds: FixedPoint,
    normalized_time_remaining: FixedPoint,
    interface: HyperdriveInterface,
    pool_state: PoolState,
) -> FixedPoint:
    """Calculate the shares received for a given amount of bonds, after fees.

    Arguments
    ---------
    amount_bonds: FixedPoint
        The amount of bonds to be exchanged.
    normalized_time_remaining: FixedPoint
        Time to maturity, normalized to 1.
    interface: HyperdriveInterface
        The Hyperdrive API interface object.
    pool_state: PoolState, optional
        The hyperdrive pool state.

    Returns
    -------
    FixedPoint
        The shares received for a given amount of bonds, after fees.
    """
    curve_part_shares_after_fees = 0
    if normalized_time_remaining > FixedPoint(0):
        curve_part_bonds = amount_bonds * normalized_time_remaining
        curve_part_shares = interface.calc_shares_out_given_bonds_in_down(abs(curve_part_bonds), pool_state)
        price_discount = FixedPoint(1) - interface.calc_spot_price(pool_state)
        curve_part_fees = curve_part_shares * price_discount * pool_state.pool_config.fees.curve
        curve_part_shares_after_fees = curve_part_shares - curve_part_fees
    flat_part_shares = amount_bonds * (FixedPoint(1) - normalized_time_remaining) / pool_state.pool_info.share_price
    flat_part_fees = flat_part_shares * pool_state.pool_config.fees.flat
    flat_part_shares_after_fees = flat_part_shares - flat_part_fees
    return curve_part_shares_after_fees + flat_part_shares_after_fees


def calculate_close_short_flat_plus_curve(
    amount_bonds: FixedPoint,
    normalized_time_remaining: FixedPoint,
    interface: HyperdriveInterface,
    pool_state: PoolState | None = None,
) -> FixedPoint:
    """Calculate the shares received for a given amount of bonds, after fees.

    Arguments
    ---------
    amount_bonds: FixedPoint
        The amount of bonds to be exchanged.
    normalized_time_remaining: FixedPoint
        Time to maturity, normalized to 1.
    interface: HyperdriveInterface
        The Hyperdrive API interface object.
    pool_state: PoolState, optional
        The hyperdrive pool state.

    Returns
    -------
    FixedPoint
        The shares received for a given amount of bonds, after fees.
    """
    if pool_state is None:
        pool_state = interface.current_pool_state
    curve_part_shares_after_fees = 0
    if normalized_time_remaining > FixedPoint(0):
        curve_part_bonds = amount_bonds * normalized_time_remaining
        curve_part_shares = interface.calc_shares_in_given_bonds_out_up(abs(curve_part_bonds), pool_state)
        price_discount = FixedPoint(1) - interface.calc_spot_price(pool_state)
        curve_part_fees = curve_part_shares * price_discount * pool_state.pool_config.fees.curve
        curve_part_shares_after_fees = curve_part_shares - curve_part_fees
    flat_part_shares = amount_bonds * (FixedPoint(1) - normalized_time_remaining) / pool_state.pool_info.share_price
    flat_part_fees = flat_part_shares * pool_state.pool_config.fees.flat
    flat_part_shares_after_fees = flat_part_shares - flat_part_fees
    return curve_part_shares_after_fees + flat_part_shares_after_fees


def calculate_short_proceeds(bond_amount, share_amount, open_share_price, share_price, flat_fee):
    """Calculate the share proceeds of closing a short position, in base.

    proceeds = (c1 / c0 + flat_fee) * dy - c * dz
             = (share_price / open_share_price + flat_fee) * bond_amount - share_price * share_amount

    Arguments
    ---------
    bond_amount: int
        The amount of bonds to be exchanged.
    share_amount: int
        The amount of shares to be exchanged.
    open_share_price: int
        The open share price.
    share_price: int
        The share price.
    flat_fee: int
        The flat fee.

    Returns
    -------
    int
        The share proceeds of closing a short position, in base.
    """
    return (share_price / open_share_price + flat_fee) * bond_amount - share_price * share_amount


def calc_single_closeout(
    position: pd.Series,
    contract: Contract,
    interface: HyperdriveInterface,
    min_output: int,
    lp_share_price: FixedPoint,
    block_time: int,
    position_duration: int,
    share_price: FixedPoint,
    pool_state: PoolState,
) -> Decimal:
    """Calculate the closeout pnl for a single position.

    Arguments
    ---------
    position: pd.DataFrame
        The position to calculate the closeout pnl for (one row in current_wallet)
    interface: HyperdriveInterface
        The Hyperdrive API interface object
    contract: Contract
        The contract object
    min_output: int
        The minimum output to be accepted, as part of slippage tolerance
    lp_share_price: FixedPoint
        The value of one LP share in units of the base token
    block_time: int
        The current block time
    position_duration: int
        The position duration
    share_price: FixedPoint
        The share price
    pool_state: PoolState
        The hyperdrive pool state

    Returns
    -------
    Decimal
        The closeout pnl
    """
    # pylint: disable=too-many-locals,too-many-arguments
    # pnl is itself
    if position["base_token_type"] == BASE_TOKEN_SYMBOL:
        return position["value"]
    if position["value"] == 0:
        return Decimal(0)
    assert len(position.shape) == 1, "Only one position at a time"
    amount = FixedPoint(f"{position['value']:f}").scaled_value
    tokentype = position["base_token_type"]
    assert isinstance(tokentype, str)
    address = position["wallet_address"]
    sender = ChecksumAddress(HexAddress(HexStr(address)))
    preview_result = None
    out_pnl = Decimal("nan")
    if tokentype in ["LONG", "SHORT"]:
        maturity = position["maturity_time"]
        assert isinstance(maturity, Decimal)
        maturity = int(maturity)
        assert isinstance(maturity, int)
        normalized_time_remaining = (maturity - block_time) / position_duration
        if tokentype == "LONG":
            fn_args = (
                maturity,
                amount,
                min_output,
                (  # IHyperdrive.Options
                    address,  # destination
                    True,  # asBase
                    bytes(0),  # extraData
                ),
            )
            try:
                preview_result = smart_contract_preview_transaction(
                    contract, sender, "closeLong", *fn_args, block_number=position["block_number"]
                )
                out_pnl = Decimal(preview_result["value"]) / Decimal(1e18)
            except Exception as exception:  # pylint: disable=broad-except
                out_pnl = (
                    calculate_close_long_flat_plus_curve(
                        amount, FixedPoint(normalized_time_remaining), interface, pool_state
                    )
                    * share_price
                )
                out_pnl = Decimal(out_pnl.scaled_value) / Decimal(1e18)
                logging.warning("Exception caught, ignoring: %s", exception)
        elif tokentype == "SHORT":
            fn_args = (
                maturity,
                amount,
                min_output,
                (  # IHyperdrive.Options
                    address,  # destination
                    True,  # asBase
                    bytes(0),  # extraData
                ),
            )
            try:
                preview_result = smart_contract_preview_transaction(
                    contract, sender, "closeShort", *fn_args, block_number=position["block_number"]
                )
                out_pnl = preview_result["value"] / Decimal(1e18)
            except Exception as exception:  # pylint: disable=broad-except
                logging.warning("Exception caught, ignoring: %s", exception)

    elif tokentype in ["LP", "WITHDRAWAL_SHARE"]:
        out_pnl = amount * lp_share_price
        out_pnl = Decimal(out_pnl.scaled_value) / Decimal(1e18)
    else:
        # Should never get here
        raise ValueError(f"Unexpected token type: {tokentype}")
    return out_pnl


def calc_closeout_pnl(
    current_wallet: pd.DataFrame,
    hyperdrive_contract: Contract,
    interface: HyperdriveInterface,
) -> pd.DataFrame:
    """Calculate closeout value of agent positions.

    Arguments
    ---------
    current_wallet: pd.DataFrame
        A dataframe resulting from `get_current_wallet` that describes the current wallet position.
    hyperdrive_contract: Contract
        The hyperdrive contract object.
    interface: HyperdriveInterface
        The Hyperdrive interface object.

    Returns
    -------
    Decimal
        The closeout pnl
    """
    pool_state = interface.current_pool_state
    return current_wallet.apply(
        calc_single_closeout,  # type: ignore
        contract=hyperdrive_contract,
        interface=interface,
        min_output=0,
        lp_share_price=pool_state.pool_info.lp_share_price,
        block_time=pool_state.block_time,
        position_duration=pool_state.pool_config.position_duration,
        share_price=pool_state.pool_info.share_price,
        pool_state=pool_state,
        axis=1,
    )
