"""Helper functions to export data to csv from the db and to load csv to dataframes."""

from __future__ import annotations

import logging
import os
from typing import Type

import pandas as pd
from sqlalchemy import exc
from sqlalchemy.orm import Session

from agent0.chainsync.db.base import (
    AddrToUsername,
    Base,
    UsernameToUser,
    get_addr_to_username,
    get_username_to_user,
    initialize_session,
)

from .interface import (
    get_checkpoint_info,
    get_current_wallet,
    get_pool_analysis,
    get_pool_config,
    get_pool_info,
    get_ticker,
    get_transactions,
    get_wallet_deltas,
    get_wallet_pnl,
)
from .schema import (
    CheckpointInfo,
    CurrentWallet,
    HyperdriveTransaction,
    PoolAnalysis,
    PoolConfig,
    PoolInfo,
    Ticker,
    WalletDelta,
    WalletPNL,
)

MAX_BATCH_SIZE = 10000


def export_db_to_file(out_dir: str, db_session: Session | None = None, raw: bool = False) -> None:
    """Export all tables from the database and write as parquet files, one per table.
    We use parquet since it's type aware, so all original types (including Decimals) are preserved
    when read

    Arguments
    ---------
    out_dir: str
        The directory to write the parquet files to. It's assumed this directory already exists.
    db_session: Session | None, optional
        The initialized session object. If none, will read credentials from `postgres.env`
    raw: bool, optional
        If true, won't add any additional columns to the output. Used for save/load state in db.
    """
    if db_session is None:
        # postgres session
        db_session = initialize_session()

    # TODO there might be a way to make this all programmatic by reading the schema
    if raw:
        return_timestamps = False
    else:
        return_timestamps = True

    # Base tables
    get_addr_to_username(db_session).to_parquet(
        os.path.join(out_dir, "addr_to_username.parquet"), index=False, engine="pyarrow"
    )
    get_username_to_user(db_session).to_parquet(
        os.path.join(out_dir, "username_to_user.parquet"), index=False, engine="pyarrow"
    )

    # Hyperdrive tables
    get_pool_config(db_session, coerce_float=False).to_parquet(
        os.path.join(out_dir, "pool_config.parquet"), index=False, engine="pyarrow"
    )
    get_checkpoint_info(db_session, coerce_float=False).to_parquet(
        os.path.join(out_dir, "checkpoint_info.parquet"), index=False, engine="pyarrow"
    )
    get_pool_info(db_session, coerce_float=False).to_parquet(
        os.path.join(out_dir, "pool_info.parquet"), index=False, engine="pyarrow"
    )
    get_wallet_deltas(db_session, coerce_float=False, return_timestamp=return_timestamps).to_parquet(
        os.path.join(out_dir, "wallet_delta.parquet"), index=False, engine="pyarrow"
    )
    # TODO input_params_maxDeposit is too large of a number to be stored in parquet
    # so we coerce_float here for data export purposes.
    get_transactions(db_session, coerce_float=True).to_parquet(
        os.path.join(out_dir, "transactions.parquet"), index=False, engine="pyarrow"
    )

    ## Analysis tables
    get_pool_analysis(db_session, coerce_float=False, return_timestamp=return_timestamps).to_parquet(
        os.path.join(out_dir, "pool_analysis.parquet"), index=False, engine="pyarrow"
    )
    get_current_wallet(db_session, coerce_float=False, raw=raw).to_parquet(
        os.path.join(out_dir, "current_wallet.parquet"), index=False, engine="pyarrow"
    )
    get_ticker(db_session, coerce_float=False).to_parquet(
        os.path.join(out_dir, "ticker.parquet"), index=False, engine="pyarrow"
    )
    get_wallet_pnl(db_session, coerce_float=False, return_timestamp=return_timestamps).to_parquet(
        os.path.join(out_dir, "wallet_pnl.parquet"), index=False, engine="pyarrow"
    )


def import_to_pandas(in_dir: str) -> dict[str, pd.DataFrame]:
    """Helper function to load data from parquet

    Arguments
    ---------
    in_dir: str
        The directory to read the parquet files from that matches the out_dir passed into export_db_to_file

    Returns
    -------
    dict[str, pd.DataFrame]
        A dictionary of pandas dataframes keyed by the original table name in the db
    """
    out = {}

    out["addr_to_username"] = pd.read_parquet(os.path.join(in_dir, "addr_to_username.parquet"), engine="pyarrow")
    out["username_to_user"] = pd.read_parquet(os.path.join(in_dir, "username_to_user.parquet"), engine="pyarrow")
    out["pool_config"] = pd.read_parquet(os.path.join(in_dir, "pool_config.parquet"), engine="pyarrow")
    out["checkpoint_info"] = pd.read_parquet(os.path.join(in_dir, "checkpoint_info.parquet"), engine="pyarrow")
    out["pool_info"] = pd.read_parquet(os.path.join(in_dir, "pool_info.parquet"), engine="pyarrow")
    out["wallet_delta"] = pd.read_parquet(os.path.join(in_dir, "wallet_delta.parquet"), engine="pyarrow")
    out["transactions"] = pd.read_parquet(os.path.join(in_dir, "transactions.parquet"), engine="pyarrow")
    out["pool_analysis"] = pd.read_parquet(os.path.join(in_dir, "pool_analysis.parquet"), engine="pyarrow")
    out["current_wallet"] = pd.read_parquet(os.path.join(in_dir, "current_wallet.parquet"), engine="pyarrow")
    out["ticker"] = pd.read_parquet(os.path.join(in_dir, "ticker.parquet"), engine="pyarrow")
    out["wallet_pnl"] = pd.read_parquet(os.path.join(in_dir, "wallet_pnl.parquet"), engine="pyarrow")
    return out


def import_to_db(db_session: Session, in_dir: str, drop=True) -> None:
    """Helper function to load data from parquet into the db

    Arguments
    ---------
    db_session: Session
        The sqlalchemy session object
    in_dir: str
        The directory to read the parquet files from that matches the out_dir passed into export_db_to_file
    drop: bool, optional
        Whether to drop the existing data in the db before importing
    """
    # Drop all if drop is set

    if drop:
        db_session.query(AddrToUsername).delete()
        db_session.query(UsernameToUser).delete()
        db_session.query(PoolConfig).delete()
        db_session.query(CheckpointInfo).delete()
        db_session.query(PoolInfo).delete()
        db_session.query(WalletDelta).delete()
        db_session.query(HyperdriveTransaction).delete()
        db_session.query(PoolAnalysis).delete()
        db_session.query(CurrentWallet).delete()
        db_session.query(Ticker).delete()
        db_session.query(WalletPNL).delete()
        try:
            db_session.commit()
        except exc.DataError as err:
            db_session.rollback()
            logging.error("Error on adding wallet_infos: %s", err)
            raise err

    out = import_to_pandas(in_dir)
    _df_to_db(out["addr_to_username"], AddrToUsername, db_session)
    _df_to_db(out["username_to_user"], UsernameToUser, db_session)
    _df_to_db(out["pool_config"], PoolConfig, db_session)
    _df_to_db(out["checkpoint_info"], CheckpointInfo, db_session)
    _df_to_db(out["pool_info"], PoolInfo, db_session)
    _df_to_db(out["wallet_delta"], WalletDelta, db_session)
    _df_to_db(out["transactions"], HyperdriveTransaction, db_session)
    _df_to_db(out["pool_analysis"], PoolAnalysis, db_session)
    _df_to_db(out["current_wallet"], CurrentWallet, db_session)
    _df_to_db(out["ticker"], Ticker, db_session)
    _df_to_db(out["wallet_pnl"], WalletPNL, db_session)


def _df_to_db(insert_df: pd.DataFrame, schema_obj: Type[Base], session: Session):
    """Helper function to add a dataframe to a database"""
    table_name = schema_obj.__tablename__

    # dataframe to_sql needs data types from the schema object
    dtype = {c.name: c.type for c in schema_obj.__table__.columns}
    # Pandas doesn't play nice with types
    insert_df.to_sql(
        table_name,
        con=session.connection(),
        method="multi",
        # if_exists=if_exists_method,
        if_exists="append",
        index=False,
        dtype=dtype,  # type: ignore
        chunksize=MAX_BATCH_SIZE,
    )
    # commit the transaction
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error on adding %s: %s", table_name, err)
        raise err
