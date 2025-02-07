"""Functions to gather data from postgres, do analysis, and add back into postgres."""

from __future__ import annotations

import pandas as pd
from sqlalchemy.orm import Session

from agent0.chainsync.db.hyperdrive import (
    DBPositionSnapshot,
    get_current_positions,
    get_latest_block_number_from_positions_snapshot_table,
)
from agent0.chainsync.df_to_db import df_to_db
from agent0.ethpy.hyperdrive import HyperdriveReadInterface

from .calc_position_value import fill_pnl_values

pd.set_option("display.max_columns", None)


def db_to_analysis(
    db_session: Session,
    interfaces: list[HyperdriveReadInterface],
    block_number: int,
    calc_pnl: bool = True,
) -> None:
    """Function to query postgres data tables and insert to analysis tables.
    Executes analysis on a batch of blocks, defined by start and end block.

    Arguments
    ---------
    db_session: Session
        The initialized db session.
    interfaces: list[HyperdriveReadInterface]
        A collection of Hyperdrive interface objects, each connected to a pool.
    block_number: int
        The block number to run analysis on.
    calc_pnl: bool, optional
        Whether to calculate pnl. Defaults to True.
    """

    # Snapshot wallet to table.
    # This function takes care of not adding duplicate entries.
    # TODO there may be time and memory concerns here if we're spinning up from
    # scratch and there's lots of trades/pools.
    snapshot_positions_to_db(
        interfaces,
        wallet_addr=None,
        calc_pnl=calc_pnl,
        db_session=db_session,
        block_number=block_number,
    )


def snapshot_positions_to_db(
    interfaces: list[HyperdriveReadInterface],
    wallet_addr: str | None,
    calc_pnl: bool,
    db_session: Session,
    block_number: int,
):
    """Function to query the trade events table and takes a snapshot
    of the current positions and pnl.

    .. note::
        This function does not scale well in simulation mode, as this table grows
        for all wallets, for all positions, for every snapshot period (currently set to every block).

        We can try to alleviate this by (1) increasing the snapshot period, and (2) removing
        duplicate entries of closed positions (since their `realized_value` never changes).

        This shouldn't be a problem for remote mode, as we limit this table to (1) only
        agents managed by agent0, and (2) only adds an entry for every explicit "get_all_positions"
        call.

    Arguments
    ---------
    interfaces: list[HyperdriveReadInterface]
        A collection of Hyperdrive interface objects, each connected to a pool.
    wallet_addr: str | None
        The wallet address to query. If None, will not filter events by wallet addr.
    db_session: Session
        The database session.
    calc_pnl: bool
        Whether to calculate pnl.
    block_number: int
        The block number to snapshot positions on.
    """
    assert len(interfaces) > 0

    all_pool_positions: list[pd.DataFrame] = []
    for interface in interfaces:
        # TODO filter by hyperdrive address here
        last_snapshot_block = get_latest_block_number_from_positions_snapshot_table(
            db_session, wallet_addr, hyperdrive_address=interface.hyperdrive_address
        )
        if block_number <= last_snapshot_block:
            continue

        # Calculate all open positions for the end block
        # We need to keep zero balances to keep track of
        # the pnl after close, and to keep a record for
        # this snapshot.
        current_pool_positions = get_current_positions(
            db_session,
            wallet_addr=wallet_addr,
            hyperdrive_address=interface.hyperdrive_address,
            query_block=block_number + 1,  # Query block numbers are not inclusive
            show_closed_positions=True,
            coerce_float=False,
        )
        if len(current_pool_positions) > 0:
            # Add missing columns
            current_pool_positions["block_number"] = block_number
            # Calculate pnl for these positions if flag is set
            if calc_pnl:
                current_pool_positions = fill_pnl_values(
                    current_pool_positions, db_session, interface, coerce_float=False
                )
            all_pool_positions.append(current_pool_positions)

    if len(all_pool_positions) > 0:
        # Add wallet_pnl to the database
        df_to_db(pd.concat(all_pool_positions, axis=0), DBPositionSnapshot, db_session)
