"""Calculates the pnl."""

from __future__ import annotations

import logging
import os
from decimal import Decimal

import pandas as pd
from fixedpointmath import FixedPoint

from agent0.ethpy.hyperdrive import HyperdriveReadInterface
from agent0.ethpy.hyperdrive.state import PoolState


# Define a context manager to suppress stdout and stderr.
# We keep this as camel case due to it being a context manager
# pylint: disable=invalid-name
class _suppress_stdout_stderr:
    """A context manager for doing a "deep suppression" of stdout and stderr in
    Python, i.e. will suppress all print, even if the print originates in a
    compiled C/Fortran sub-function.

    This will not suppress raised exceptions, since exceptions are printed
    to stderr just before a script exits, and after the context manager has
    exited (at least, I think that is why it lets exceptions through).
    """

    def __init__(self):
        # Open a pair of null files
        self.null_fds = [os.open(os.devnull, os.O_RDWR) for x in range(2)]
        # Save the actual stdout (1) and stderr (2) file descriptors.
        self.save_fds = [os.dup(1), os.dup(2)]

    def __enter__(self):
        # Assign the null pointers to stdout and stderr.
        os.dup2(self.null_fds[0], 1)
        os.dup2(self.null_fds[1], 2)

    def __exit__(self, *_):
        # Re-assign the real stdout/stderr back to (1) and (2)
        os.dup2(self.save_fds[0], 1)
        os.dup2(self.save_fds[1], 2)
        # Close all file descriptors
        for fd in self.null_fds + self.save_fds:
            os.close(fd)


def calc_single_closeout(
    position: pd.Series,
    interface: HyperdriveReadInterface,
    hyperdrive_state: PoolState,
    checkpoint_share_prices: pd.Series,
) -> Decimal:
    """Calculate the closeout value for a single position.

    Arguments
    ---------
    position: pd.DataFrame
        The position to calculate the closeout value for (one row in current_wallet).
    interface: HyperdriveReadInterface
        The hyperdrive read interface.
    hyperdrive_state: PoolState
        The hyperdrive pool state.
    checkpoint_share_prices: pd.Series
        A series with the index as checkpoint time and the value as the share prices.

    Returns
    -------
    Decimal
        The closeout position value.
    """
    # If no balance, value is 0
    if position["token_balance"] == 0:
        return Decimal(0)
    amount = FixedPoint(f"{position['token_balance']:f}")
    token_type = position["token_type"]
    maturity = 0
    position_duration = hyperdrive_state.pool_config.position_duration

    if token_type in ["LONG", "SHORT"]:
        maturity = int(position["maturity_time"])

    out_value = Decimal("nan")
    if token_type == "LONG":
        try:
            # Suppress any errors coming from rust here, we already log it as info
            with _suppress_stdout_stderr():
                out_value = interface.calc_close_long(amount, maturity, hyperdrive_state)
        # Rust Panic Exceptions are base exceptions, not Exceptions
        except BaseException as exception:  # pylint: disable=broad-except
            logging.info("Chainsync: Exception caught in calculating close long, ignoring: %s", exception)
        # FixedPoint to Decimal
        out_value = Decimal(str(out_value))

    elif token_type == "SHORT":
        # Get the open share price from the checkpoint lookup
        open_checkpoint_time = maturity - position_duration

        # Use checkpoint events to get checkpoint share price.
        # NOTE: anvil doesn't keep events past a certain point
        # so checkpoint events may be missing if we fork a chain.
        # We detect this case, print a warning, and set value to NaN.
        if open_checkpoint_time not in checkpoint_share_prices.index:
            if open_checkpoint_time < checkpoint_share_prices.index.min():
                logging.warning(
                    "Chainsync: Missing checkpoint event data for short position, event history likely lost."
                )
                return Decimal("nan")
            # If we have events and open checkpoint time still missing, something very wrong.
            raise ValueError("Chainsync: Missing checkpoint event data for short position.")

        open_share_price = checkpoint_share_prices.loc[open_checkpoint_time]
        # Sanity check, the getter of checkpoint share price should only select distinct
        # so this should be a singular int instead of a series.
        assert isinstance(open_share_price, Decimal)
        open_share_price = FixedPoint(open_share_price)

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
            # Suppress any errors coming from rust here, we already log it as info
            with _suppress_stdout_stderr():
                out_value = interface.calc_close_short(
                    amount,
                    open_vault_share_price=open_share_price,
                    close_vault_share_price=close_share_price,
                    maturity_time=maturity,
                    pool_state=hyperdrive_state,
                )
        # Rust Panic Exceptions are base exceptions, not Exceptions
        except BaseException as exception:  # pylint: disable=broad-except
            logging.info("Chainsync: Exception caught in calculating close short, ignoring: %s", exception)
        out_value = Decimal(str(out_value))

    # For PNL, we assume all withdrawal shares are redeemable
    # even if there are no withdrawal shares available to withdraw
    # Hence, we don't use preview transaction here
    elif token_type in ["LP", "WITHDRAWAL_SHARE"]:
        out_value = amount * hyperdrive_state.pool_info.lp_share_price
        out_value = Decimal(str(out_value))
    else:
        # Should never get here
        raise ValueError(f"Unexpected token type: {token_type}")
    return out_value


def calc_closeout_value(
    current_positions: pd.DataFrame,
    checkpoint_info: pd.DataFrame,
    interface: HyperdriveReadInterface,
    block_number: int,
) -> pd.Series:
    """Calculate closeout value of agent positions.

    Arguments
    ---------
    current_positions: pd.DataFrame
        A dataframe resulting from `get_current_wallet` that describes the current wallet position.
    checkpoint_info: pd.DataFrame
        A dataframe resulting from `get_checkpoint_info` that describes all checkpoints.
    interface: HyperdriveReadInterface
        The hyperdrive read interface.
    block_number: int
        The block number to calculate closeout value on.

    Returns
    -------
    pd.Series
        A series matching the current_wallet input that contains the values of each position.
    """

    # Sanity check, the block number across all current wallets should be identical
    assert len(current_positions) > 0
    assert current_positions["block_number"].nunique() == 1

    # Get the pool state at this position
    block_number = int(current_positions["block_number"].iloc[0])
    hyperdrive_state = interface.get_hyperdrive_state(interface.get_block(block_number))

    # Prepare the checkpoint info dataframe for lookups based on checkpoint time
    checkpoint_share_prices = checkpoint_info.set_index("checkpoint_time")["checkpoint_vault_share_price"]

    # Calculate closeout value per row of dataframe
    return current_positions.apply(
        calc_single_closeout,  # type: ignore
        interface=interface,
        hyperdrive_state=hyperdrive_state,
        checkpoint_share_prices=checkpoint_share_prices,
        axis=1,
    )
