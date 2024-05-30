"""Helper functions to export data to csv from the db and to load csv to dataframes."""

from __future__ import annotations

import logging
from pathlib import Path

import pandas as pd
from sqlalchemy import exc
from sqlalchemy.orm import Session

from agent0.chainsync.db.base import AddrToUsername, get_addr_to_username, initialize_session
from agent0.chainsync.df_to_db import df_to_db

from .interface import (
    get_checkpoint_info,
    get_hyperdrive_addr_to_name,
    get_pool_config,
    get_pool_info,
    get_position_snapshot,
    get_trade_events,
)
from .schema import CheckpointInfo, HyperdriveAddrToName, PoolConfig, PoolInfo, PositionSnapshot, TradeEvent


def export_db_to_file(out_dir: Path, db_session: Session | None = None) -> None:
    """Export all tables from the database and write as parquet files, one per table.
    We use parquet since it's type aware, so all original types (including Decimals) are preserved
    when read

    Arguments
    ---------
    out_dir: Path
        The directory to write the parquet files to. It's assumed this directory already exists.
    db_session: Session | None, optional
        The initialized session object. If none, will read credentials from `.env`
    """
    if db_session is None:
        # postgres session
        db_session = initialize_session()

    # Base tables
    get_addr_to_username(db_session).to_parquet(out_dir / "addr_to_username.parquet", index=False, engine="pyarrow")

    # Hyperdrive tables
    get_hyperdrive_addr_to_name(db_session).to_parquet(
        out_dir / "hyperdrive_addr_to_name.parquet", index=False, engine="pyarrow"
    )
    get_trade_events(db_session, all_token_deltas=True).to_parquet(
        out_dir / "trade_event.parquet", index=False, engine="pyarrow"
    )
    get_pool_config(db_session, coerce_float=False).to_parquet(
        out_dir / "pool_config.parquet", index=False, engine="pyarrow"
    )
    get_checkpoint_info(db_session, coerce_float=False).to_parquet(
        out_dir / "checkpoint_info.parquet", index=False, engine="pyarrow"
    )
    get_pool_info(db_session, coerce_float=False).to_parquet(
        out_dir / "pool_info.parquet", index=False, engine="pyarrow"
    )
    get_position_snapshot(db_session, coerce_float=False).to_parquet(
        out_dir / "position_snapshot.parquet", index=False, engine="pyarrow"
    )


def import_to_pandas(in_dir: Path) -> dict[str, pd.DataFrame]:
    """Helper function to load data from parquet

    Arguments
    ---------
    in_dir: Path
        The directory to read the parquet files from that matches the out_dir passed into export_db_to_file

    Returns
    -------
    dict[str, pd.DataFrame]
        A dictionary of pandas dataframes keyed by the original table name in the db
    """
    out = {}

    out["addr_to_username"] = pd.read_parquet(in_dir / "addr_to_username.parquet", engine="pyarrow")
    out["hyperdrive_addr_to_name"] = pd.read_parquet(in_dir / "hyperdrive_addr_to_name.parquet", engine="pyarrow")
    out["trade_event"] = pd.read_parquet(in_dir / "trade_event.parquet", engine="pyarrow")
    out["pool_config"] = pd.read_parquet(in_dir / "pool_config.parquet", engine="pyarrow")
    out["checkpoint_info"] = pd.read_parquet(in_dir / "checkpoint_info.parquet", engine="pyarrow")
    out["pool_info"] = pd.read_parquet(in_dir / "pool_info.parquet", engine="pyarrow")
    out["position_snapshot"] = pd.read_parquet(in_dir / "position_snapshot.parquet", engine="pyarrow")
    return out


def import_to_db(db_session: Session, in_dir: Path, drop=True) -> None:
    """Helper function to load data from parquet into the db

    Arguments
    ---------
    db_session: Session
        The sqlalchemy session object
    in_dir: Path
        The directory to read the parquet files from that matches the out_dir passed into export_db_to_file
    drop: bool, optional
        Whether to drop the existing data in the db before importing
    """
    # Drop all if drop is set

    if drop:
        db_session.query(AddrToUsername).delete()
        db_session.query(HyperdriveAddrToName).delete()
        db_session.query(TradeEvent).delete()
        db_session.query(PoolConfig).delete()
        db_session.query(CheckpointInfo).delete()
        db_session.query(PoolInfo).delete()
        db_session.query(PositionSnapshot).delete()
        try:
            db_session.commit()
        except exc.DataError as err:
            db_session.rollback()
            logging.error("Error on adding wallet_infos: %s", err)
            raise err

    out = import_to_pandas(in_dir)
    df_to_db(out["addr_to_username"], AddrToUsername, db_session)
    df_to_db(out["hyperdrive_addr_to_name"], HyperdriveAddrToName, db_session)
    df_to_db(out["trade_event"], TradeEvent, db_session)
    df_to_db(out["pool_config"], PoolConfig, db_session)
    df_to_db(out["checkpoint_info"], CheckpointInfo, db_session)
    df_to_db(out["pool_info"], PoolInfo, db_session)
    df_to_db(out["position_snapshot"], PositionSnapshot, db_session)
