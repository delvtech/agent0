"""Calculates the pnl."""
from __future__ import annotations

import logging
from decimal import Decimal

import pandas as pd
from eth_typing import ChecksumAddress, HexAddress, HexStr
from ethpy.base import smart_contract_preview_transaction
from ethpy.hyperdrive import BASE_TOKEN_SYMBOL
from fixedpointmath import FixedPoint
from web3.contract.contract import Contract


def calc_single_closeout(position: pd.Series, contract: Contract, pool_info: pd.DataFrame, min_output: int) -> Decimal:
    """Calculate the closeout pnl for a single position.

    Arguments
    ---------
    position: pd.DataFrame
        The position to calculate the closeout pnl for (one row in current_wallet)
    contract: Contract
        The contract object
    pool_info: pd.DataFrame
        The pool info
    min_output: int
        The minimum output to be accepted, as part of slippage tolerance

    Returns
    -------
    Decimal
        The closeout pnl
    """
    # pnl is itself
    if position["base_token_type"] == BASE_TOKEN_SYMBOL:
        return position["value"]
    # If no value, pnl is 0
    if position["value"] == 0:
        return Decimal(0)
    assert len(position.shape) == 1, "Only one position at a time"
    amount = FixedPoint(f"{position['value']:f}").scaled_value
    address = position["wallet_address"]
    tokentype = position["base_token_type"]
    sender = ChecksumAddress(HexAddress(HexStr(address)))
    preview_result = None
    maturity = 0
    if tokentype in ["LONG", "SHORT"]:
        maturity = position["maturity_time"]
        assert isinstance(maturity, Decimal)
        maturity = int(maturity)
        assert isinstance(maturity, int)
    assert isinstance(tokentype, str)

    out_pnl = Decimal("nan")

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

    elif tokentype == "LP":
        fn_args = (
            amount,
            min_output,
            (  # IHyperdrive.Options
                address,  # destination
                True,  # asBase
                bytes(0),  # extraData
            ),
        )
        # If this fails, keep as nan and continue iterating
        try:
            preview_result = smart_contract_preview_transaction(
                contract, sender, "removeLiquidity", *fn_args, block_number=position["block_number"]
            )
            out_pnl = Decimal(
                preview_result["baseProceeds"]
                # We assume all withdrawal shares are redeemable
                + preview_result["withdrawalShares"] * pool_info["lp_share_price"].values[-1]
            ) / Decimal(1e18)
        except Exception as exception:  # pylint: disable=broad-except
            logging.warning("Exception caught, ignoring: %s", exception)

    elif tokentype == "WITHDRAWAL_SHARE":
        fn_args = (
            amount,
            min_output,
            (  # IHyperdrive.Options
                address,  # destination
                True,  # asBase
                bytes(0),  # extraData
            ),
        )
        try:
            # For PNL, we assume all withdrawal shares are redeemable
            # even if there are no withdrawal shares available to withdraw
            # Hence, we don't use preview transaction here
            out_pnl = Decimal(amount * pool_info["lp_share_price"].values[-1]) / Decimal(1e18)
        except Exception as exception:  # pylint: disable=broad-except
            logging.warning("Exception caught, ignoring: %s", exception)
    else:
        # Should never get here
        raise ValueError(f"Unexpected token type: {tokentype}")
    return out_pnl


def calc_closeout_pnl(
    current_wallet: pd.DataFrame, pool_info: pd.DataFrame, hyperdrive_contract: Contract
) -> pd.DataFrame:
    """Calculate closeout value of agent positions.

    Arguments
    ---------
    current_wallet: pd.DataFrame
        A dataframe resulting from `get_current_wallet` that describes the current wallet position.
    pool_info: pd.DataFrame
        The pool info object.
    hyperdrive_contract: Contract
        The hyperdrive contract object.

    Returns
    -------
    Decimal
        The closeout pnl
    """
    # Define a function to handle the calculation for each group
    out_pnl = current_wallet.apply(
        calc_single_closeout,  # type: ignore
        contract=hyperdrive_contract,
        pool_info=pool_info,
        min_output=0,
        axis=1,
    )

    return out_pnl
