"""Calculates the pnl."""

from __future__ import annotations

import logging
from decimal import Decimal

import pandas as pd
from fixedpointmath import FixedPoint

from agent0.ethpy.hyperdrive import BASE_TOKEN_SYMBOL, HyperdriveReadInterface
from agent0.ethpy.hyperdrive.state import PoolState


def calc_single_closeout(
    position: pd.Series,
    interface: HyperdriveReadInterface,
    hyperdrive_state: PoolState,
    checkpoint_share_prices: pd.Series,
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
    checkpoint_share_prices: pd.Series
        A series with the index as checkpoint time and the value as the share prices

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
    tokentype = position["base_token_type"]
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
        # Rust Panic Exceptions are base exceptions, not Exceptions
        except BaseException as exception:  # pylint: disable=broad-except
            logging.warning("Chainsync: Exception caught in calculating close long, ignoring: %s", exception)
        # FixedPoint to Decimal
        out_pnl = Decimal(str(out_pnl))

    elif tokentype == "SHORT":
        # Get the open share price from the checkpoint lookup
        open_checkpoint_time = maturity - position_duration
        assert (
            open_checkpoint_time in checkpoint_share_prices.index
        ), "Chainsync: open short checkpoint not found for position."
        open_share_price = FixedPoint(checkpoint_share_prices.loc[open_checkpoint_time])

        # If the position has matured, we use the share price from the checkpoint
        # Otherwise, we use the current share price
        # NOTE There exists a case where the position has matured but a checkpoint hasn't
        # been created yet. In this case, we default to using the current share price
        # this may create an PNL that might be off.
        if (hyperdrive_state.block_time >= maturity) and (maturity in checkpoint_share_prices.index):
            close_share_price = FixedPoint(checkpoint_share_prices.loc[maturity])
        else:
            close_share_price = hyperdrive_state.pool_info.vault_share_price

        try:
            out_pnl = interface.calc_close_short(
                amount,
                open_vault_share_price=open_share_price,
                close_vault_share_price=close_share_price,
                normalized_time_remaining=normalized_time_remaining,
                pool_state=hyperdrive_state,
            )
        # Rust Panic Exceptions are base exceptions, not Exceptions
        except BaseException as exception:  # pylint: disable=broad-except
            logging.warning("Chainsync: Exception caught in calculating close short, ignoring: %s", exception)
        out_pnl = Decimal(str(out_pnl))

    # For PNL, we assume all withdrawal shares are redeemable
    # even if there are no withdrawal shares available to withdraw
    # Hence, we don't use preview transaction here
    elif tokentype in ["LP", "WITHDRAWAL_SHARE"]:
        out_pnl = amount * hyperdrive_state.pool_info.lp_share_price
        out_pnl = Decimal(str(out_pnl))
    else:
        # Should never get here
        raise ValueError(f"Unexpected token type: {tokentype}")
    return out_pnl


def calc_closeout_pnl(
    current_wallet: pd.DataFrame, checkpoint_info: pd.DataFrame, interface: HyperdriveReadInterface
) -> pd.Series:
    """Calculate closeout value of agent positions.

    Arguments
    ---------
    current_wallet: pd.DataFrame
        A dataframe resulting from `get_current_wallet` that describes the current wallet position.
    checkpoint_info: pd.DataFrame
        A dataframe resulting from `get_checkpoint_info` that describes all checkpoints.
    interface: HyperdriveReadInterface
        The hyperdrive read interface

    Returns
    -------
    pd.Series
        A series matching the current_wallet input that contains the values of each position
    """

    # Sanity check, the block number across all current wallets should be identical
    assert len(current_wallet) > 0
    assert current_wallet["block_number"].nunique() == 1

    # Get the pool state at this position
    block_number = int(current_wallet["block_number"].iloc[0])
    hyperdrive_state = interface.get_hyperdrive_state(interface.get_block(block_number))

    # Prepare the checkpoint info dataframe for lookups based on checkpoint time
    checkpoint_share_prices = checkpoint_info.set_index("checkpoint_time")["vault_share_price"]

    # Calculate pnl per row of dataframe
    return current_wallet.apply(
        calc_single_closeout,  # type: ignore
        interface=interface,
        hyperdrive_state=hyperdrive_state,
        checkpoint_share_prices=checkpoint_share_prices,
        axis=1,
    )
