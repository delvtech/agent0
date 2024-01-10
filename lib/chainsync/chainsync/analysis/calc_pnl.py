"""Calculates the pnl."""
from __future__ import annotations

import logging
from decimal import Decimal

import pandas as pd
from eth_typing import ChecksumAddress, HexAddress, HexStr
from ethpy.base import smart_contract_preview_transaction
from ethpy.hyperdrive import BASE_TOKEN_SYMBOL
from fixedpointmath import FixedPoint
from hypertypes.fixedpoint_types import PoolInfoFP
from web3.contract.contract import Contract


def calc_single_closeout(
    position: pd.Series, contract: Contract, min_output: int, lp_share_price: FixedPoint
) -> Decimal:
    """Calculate the closeout pnl for a single position.

    Arguments
    ---------
    position: pd.DataFrame
        The position to calculate the closeout pnl for (one row in current_wallet)
    contract: Contract
        The contract object
    min_output: int
        The minimum output to be accepted, as part of slippage tolerance
    lp_share_price: FixedPoint
        The price of an LP share in units of the base token

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
    amount = FixedPoint(f"{position['value']:f}").scaled_value
    address = position["wallet_address"]
    tokentype = position["base_token_type"]
    sender = ChecksumAddress(HexAddress(HexStr(address)))
    preview_result = None
    maturity = 0

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

    # For PNL, we assume all withdrawal shares are redeemable
    # even if there are no withdrawal shares available to withdraw
    # Hence, we don't use preview transaction here
    elif tokentype in ["LP", "WITHDRAWAL_SHARE"]:
        out_pnl = amount * float(lp_share_price)
        out_pnl = Decimal(out_pnl) / Decimal(1e18)
    else:
        # Should never get here
        raise ValueError(f"Unexpected token type: {tokentype}")
    return out_pnl

def calc_closeout_pnl(
    current_wallet: pd.DataFrame,
    hyperdrive_contract: Contract,
    pool_info: PoolInfoFP
) -> pd.DataFrame:
    """Calculate closeout value of agent positions.

    Arguments
    ---------
    current_wallet: pd.DataFrame
        A dataframe resulting from `get_current_wallet` that describes the current wallet position.
    hyperdrive_contract: Contract
        The hyperdrive contract object.
    pool_info: PoolInfo
        Description of the pool at the point in time for which we're calculating the PNL.

    Returns
    -------
    Decimal
        The closeout pnl
    """
    return current_wallet.apply(
        calc_single_closeout,  # type: ignore
        contract=hyperdrive_contract,
        min_output=0,
        lp_share_price=pool_info.lp_share_price,
        axis=1,
    )
