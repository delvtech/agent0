"""Plots the pnl."""
from __future__ import annotations

import logging
from decimal import Decimal

import pandas as pd
from eth_typing import ChecksumAddress, HexAddress, HexStr
from ethpy.base import smart_contract_preview_transaction
from fixedpointmath import FixedPoint
from web3.contract.contract import Contract


def calc_single_closeout(
    position: pd.Series, contract: Contract, pool_info: pd.DataFrame, min_output: int, as_underlying: bool
):
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
    as_underlying: bool
        Whether or not to use the underlying token
    """
    # pnl is itself
    if position["baseTokenType"] == "BASE":
        return position["value"]
    # If no value, pnl is 0
    if position["value"] == 0:
        return Decimal(0)
    assert len(position.shape) == 1, "Only one position at a time"
    amount = FixedPoint(str(position["value"])).scaled_value
    address = position["walletAddress"]
    tokentype = position["baseTokenType"]
    sender = ChecksumAddress(HexAddress(HexStr(address)))
    preview_result = None
    maturity = 0
    if tokentype in ["LONG", "SHORT"]:
        maturity = position["maturityTime"]
        assert isinstance(maturity, Decimal)
        maturity = int(maturity)
        assert isinstance(maturity, int)
    assert isinstance(tokentype, str)
    if tokentype == "LONG":
        fn_args = (maturity, amount, min_output, address, as_underlying)
        preview_result = smart_contract_preview_transaction(
            contract, sender, "closeLong", fn_args, position["blockNumber"]
        )
        return Decimal(preview_result["value"]) / Decimal(1e18)
    elif tokentype == "SHORT":
        fn_args = (maturity, amount, min_output, address, as_underlying)
        preview_result = smart_contract_preview_transaction(
            contract, sender, "closeShort", fn_args, position["blockNumber"]
        )
        return preview_result["value"] / Decimal(1e18)
    elif tokentype == "LP":
        fn_args = (amount, min_output, address, as_underlying)
        # If this fails, keep as nan and continue iterating
        preview_result = smart_contract_preview_transaction(
            contract, sender, "removeLiquidity", fn_args, position["blockNumber"]
        )
        return Decimal(
            preview_result["baseProceeds"]
            + preview_result["withdrawalShares"]
            * pool_info["sharePrice"].values[-1]
            * pool_info["lpSharePrice"].values[-1]
        ) / Decimal(1e18)
    elif tokentype == "WITHDRAWAL_SHARE":
        fn_args = (amount, min_output, address, as_underlying)
        preview_result = smart_contract_preview_transaction(
            contract, sender, "redeemWithdrawalShares", fn_args, position["blockNumber"]
        )
        return preview_result["proceeds"] / Decimal(1e18)
    # Should never get here
    raise ValueError(f"Unexpected token type: {tokentype}")


def calc_closeout_pnl(
    current_wallet: pd.DataFrame, pool_info: pd.DataFrame, hyperdrive_contract: Contract
) -> pd.DataFrame:
    """Calculate closeout value of agent positions."""

    # Define a function to handle the calculation for each group
    out_pnl = current_wallet.apply(
        calc_single_closeout,  # type: ignore
        contract=hyperdrive_contract,
        pool_info=pool_info,
        min_output=0,
        as_underlying=True,
        axis=1,
    )

    return out_pnl
