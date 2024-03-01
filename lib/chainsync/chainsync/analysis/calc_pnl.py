"""Calculates the pnl."""

from __future__ import annotations

import logging
from decimal import Decimal

import pandas as pd
from eth_typing import ChecksumAddress, HexAddress, HexStr
from ethpy.base import smart_contract_preview_transaction
from ethpy.hyperdrive import BASE_TOKEN_SYMBOL, HyperdriveReadInterface
from ethpy.hyperdrive.state import PoolState
from fixedpointmath import FixedPoint
from web3.types import BlockIdentifier


def calc_single_closeout(
    position: pd.Series, interface: HyperdriveReadInterface, hyperdrive_state: PoolState
) -> Decimal:
    """Calculate the closeout pnl for a single position.

    Arguments
    ---------
    position: pd.DataFrame
        The position to calculate the closeout pnl for (one row in current_wallet)
    interface: HyperdriveReadInterface
        The hyperdrive read interface
    hyperdrive_state: PoolState
        The hyperdrive pool state

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
    amount = FixedPoint(f"{position['value']:f}")
    address = position["wallet_address"]
    tokentype = position["base_token_type"]
    sender = ChecksumAddress(HexAddress(HexStr(address)))
    preview_result = None
    maturity = 0
    normalized_time_remaining = FixedPoint(0)
    position_duration = hyperdrive_state.pool_config.position_duration

    if tokentype in ["LONG", "SHORT"]:
        maturity = int(position["maturity_time"])
        # If mature, set time left to 0
        normalized_time_remaining = max(maturity - hyperdrive_state.block_time, 0) / FixedPoint(position_duration)

    out_pnl = Decimal("nan")
    if tokentype == "LONG":
        try:
            out_pnl = interface.calc_close_long(amount, normalized_time_remaining, hyperdrive_state)
        except Exception as exception:  # pylint: disable=broad-except
            logging.warning("Chainsync: Exception caught in calculating close long, ignoring: %s", exception)
        # FixedPoint to Decimal
        out_pnl = Decimal(str(out_pnl))

    elif tokentype == "SHORT":
        try:
            # TODO, we need the vault share price of the open/close
            out_pnl = interface.calc_close_short()
        except Exception as exception:  # pylint: disable=broad-except
            logging.warning("Chainsync: Exception caught in calculating close short, ignoring: %s", exception)

    # For PNL, we assume all withdrawal shares are redeemable
    # even if there are no withdrawal shares available to withdraw
    # Hence, we don't use preview transaction here
    elif tokentype in ["LP", "WITHDRAWAL_SHARE"]:
        out_pnl = amount * hyperdrive_state.pool_info.lp_share_price
        out_pnl = Decimal(str(out_pnl)) / Decimal(1e18)
    else:
        # Should never get here
        raise ValueError(f"Unexpected token type: {tokentype}")
    return out_pnl


def calc_closeout_pnl(
    current_wallet: pd.DataFrame, interface: HyperdriveReadInterface, lp_share_price: FixedPoint
) -> pd.DataFrame:
    """Calculate closeout value of agent positions.

    Arguments
    ---------
    current_wallet: pd.DataFrame
        A dataframe resulting from `get_current_wallet` that describes the current wallet position.
    hyperdrive_contract: Contract
        The hyperdrive contract object.
    lp_share_price: FixedPoint
        The price of an LP share in units of the base token

    Returns
    -------
    Decimal
        The closeout pnl
    """

    # Sanity check, the block number across all current wallets should be identical
    assert len(current_wallet) > 0
    assert current_wallet["block_number"].nunique() == 1

    # Get the pool state at this position
    block_number = int(current_wallet["block_number"].iloc[0])
    hyperdrive_state = interface.get_hyperdrive_state(interface.get_block(block_number))

    return current_wallet.apply(
        calc_single_closeout,  # type: ignore
        interface=interface,
        hyperdrive_state=hyperdrive_state,
        axis=1,
    )
