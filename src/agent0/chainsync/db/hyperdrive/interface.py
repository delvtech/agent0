"""Utilities for hyperdrive related postgres interactions."""

from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import exc, func
from sqlalchemy.orm import Session

from agent0.chainsync.db.base import get_latest_block_number_from_table
from agent0.ethpy.hyperdrive import BASE_TOKEN_SYMBOL

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


def add_transactions(transactions: list[HyperdriveTransaction], session: Session) -> None:
    """Add transactions to the poolinfo table.

    Arguments
    ---------
    transactions: list[HyperdriveTransaction]
        A list of HyperdriveTransaction objects to insert into postgres
    session: Session
        The initialized session object
    """
    for transaction in transactions:
        session.add(transaction)
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error adding transaction: %s", err)
        raise err


def get_pool_config(session: Session, contract_address: str | None = None, coerce_float=True) -> pd.DataFrame:
    """Get all pool config and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    contract_address: str | None, optional
        The contract_address to filter the results on. Return all if None
    coerce_float: bool
        If True, will coerce all numeric columns to float

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool config data
    """
    query = session.query(PoolConfig)
    if contract_address is not None:
        query = query.filter(PoolConfig.contract_address == contract_address)
    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def add_pool_config(pool_config: PoolConfig, session: Session) -> None:
    """Add pool config to the pool config table if not exist.

    Verify pool config if it does exist.

    Arguments
    ---------
    pool_config: PoolConfig
        A PoolConfig object to insert into postgres
    session: Session
        The initialized session object
    """
    # NOTE the logic below is not thread safe, i.e., a race condition can exists
    # if multiple threads try to add pool config at the same time
    # This function is being called by acquire_data.py, which should only have one
    # instance per db, so no need to worry about it here
    # Since we're doing a direct equality comparison, we don't want to coerce into floats here
    existing_pool_config = get_pool_config(session, contract_address=pool_config.contract_address, coerce_float=False)
    if len(existing_pool_config) == 0:
        session.add(pool_config)
        try:
            session.commit()
        except exc.DataError as err:
            session.rollback()
            logging.error("Error adding pool_config: %s", err)
            raise err
    elif len(existing_pool_config) == 1:
        # Verify pool config
        for key in PoolConfig.__annotations__.keys():
            new_value = getattr(pool_config, key)
            old_value = existing_pool_config.loc[0, key]
            if new_value != old_value:
                raise ValueError(
                    f"Adding pool configuration field: key {key} doesn't match (new: {new_value}, old:{old_value})"
                )
    else:
        # Should never get here, contract_address is primary_key, which is unique
        raise ValueError


def add_pool_infos(pool_infos: list[PoolInfo], session: Session) -> None:
    """Add a pool info to the poolinfo table.

    Arguments
    ---------
    pool_infos: list[PoolInfo]
        A list of PoolInfo objects to insert into postgres
    session: Session
        The initialized session object
    """
    for pool_info in pool_infos:
        session.add(pool_info)
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error adding pool_infos: %s", err)
        raise err


def add_checkpoint_info(checkpoint_info: CheckpointInfo, session: Session) -> None:
    """Add checkpoint info to the checkpointinfo table if it doesn't exist.

    Arguments
    ---------
    checkpoint_info: CheckpointInfo
        A CheckpointInfo object to insert into postgres
    session: Session
        The initialized session object
    """
    # NOTE the logic below is not thread safe, i.e., a race condition can exists
    # if multiple threads try to add checkpoint info at the same time
    # This function is being called by acquire_data.py, which should only have one
    # instance per db, so no need to worry about it here
    # Since we're doing a direct equality comparison, we don't want to coerce into floats here
    existing_checkpoint_info = get_checkpoint_info(session, checkpoint_info.checkpoint_time, coerce_float=False)
    if len(existing_checkpoint_info) == 0:
        session.add(checkpoint_info)
        try:
            session.commit()
        except exc.DataError as err:
            session.rollback()
            logging.error("Error adding checkpoint info: %s", err)
            raise err
    elif len(existing_checkpoint_info) == 1:
        # Verify checkpoint info
        for key in CheckpointInfo.__annotations__.keys():
            new_value = getattr(checkpoint_info, key)
            old_value = existing_checkpoint_info.loc[0, key]
            if new_value != old_value:
                raise ValueError(f"Adding checkpoint info field: key {key} doesn't match ({new_value=}, {old_value=})")
    else:
        # Should never get here, checkpoint time is primary_key, which is unique
        raise ValueError


def add_wallet_deltas(wallet_deltas: list[WalletDelta], session: Session) -> None:
    """Add wallet deltas to the walletdelta table.

    Arguments
    ---------
    wallet_deltas: list[WalletDelta]
        A list of WalletDelta objects to insert into postgres
    session: Session
        The initialized session object
    """
    for wallet_delta in wallet_deltas:
        session.add(wallet_delta)
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error in adding wallet_deltas: %s", err)
        raise err


def get_latest_block_number_from_pool_info_table(session: Session) -> int:
    """Get the latest block number based on the pool info table in the db.

    Arguments
    ---------
    session: Session
        The initialized session object

    Returns
    -------
    int
        The latest block number in the poolinfo table
    """
    return get_latest_block_number_from_table(PoolInfo, session)


def get_latest_block_number_from_analysis_table(session: Session) -> int:
    """Get the latest block number based on the pool info table in the db.

    Arguments
    ---------
    session: Session
        The initialized session object

    Returns
    -------
    int
        The latest block number in the poolinfo table
    """
    return get_latest_block_number_from_table(PoolAnalysis, session)


def get_pool_info(
    session: Session, start_block: int | None = None, end_block: int | None = None, coerce_float=True
) -> pd.DataFrame:
    """Get all pool info and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    coerce_float: bool, optional
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data
    """
    query = session.query(PoolInfo)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_pool_info_table(session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_pool_info_table(session) + end_block + 1

    if start_block is not None:
        query = query.filter(PoolInfo.block_number >= start_block)
    if end_block is not None:
        query = query.filter(PoolInfo.block_number < end_block)

    # Always sort by time in order
    query = query.order_by(PoolInfo.timestamp)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_transactions(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    coerce_float=True,
) -> pd.DataFrame:
    """Get all transactions and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    start_block: int | None
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block: int | None
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried transactions data
    """
    query = session.query(HyperdriveTransaction)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(HyperdriveTransaction, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(HyperdriveTransaction, session) + end_block + 1

    if start_block is not None:
        query = query.filter(HyperdriveTransaction.block_number >= start_block)
    if end_block is not None:
        query = query.filter(HyperdriveTransaction.block_number < end_block)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_checkpoint_info(session: Session, checkpoint_time: int | None = None, coerce_float=True) -> pd.DataFrame:
    """Get all info associated with a given checkpoint.

    This includes
    - `checkpoint_time`: The time index of the checkpoint.
    - `vault_share_price`: The share price of the first transaction in the checkpoint.

    Arguments
    ---------
    session: Session
        The initialized session object
    checkpoint_time: int | None, optional
        The checkpoint time to filter the query on. Defaults to returning all checkpoint infos.
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried checkpoint info
    """
    query = session.query(CheckpointInfo)

    if checkpoint_time is not None:
        query = query.filter(CheckpointInfo.checkpoint_time == checkpoint_time)

    # Always sort by time in order
    query = query.order_by(CheckpointInfo.checkpoint_time)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_wallet_deltas(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    return_timestamp: bool = True,
    coerce_float=True,
) -> pd.DataFrame:
    """Get all wallet_delta data in history and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    return_timestamp: bool, optional
        Gets timestamps when looking at pool analysis. Defaults to True
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    if return_timestamp:
        query = session.query(PoolInfo.timestamp, WalletDelta)
    else:
        query = session.query(WalletDelta)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletDelta, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletDelta, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletDelta.block_number >= start_block)
    if end_block is not None:
        query = query.filter(WalletDelta.block_number < end_block)

    if return_timestamp:
        # query from PoolInfo the timestamp
        query = query.join(PoolInfo, WalletDelta.block_number == PoolInfo.block_number)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_all_traders(
    session: Session, start_block: int | None = None, end_block: int | None = None, coerce_float=True
) -> pd.Series:
    """Get the list of all traders from the WalletInfo table.

    Arguments
    ---------
    session: Session
        The initialized session object
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    list[str]
        A list of addresses that have made a trade
    """
    query = session.query(WalletDelta.wallet_address)
    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletDelta, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletDelta, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletDelta.block_number >= start_block)
    if end_block is not None:
        query = query.filter(WalletDelta.block_number < end_block)

    if query is None:
        return pd.Series([])
    query = query.distinct()

    results = pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)

    return results["wallet_address"]


# Analysis schema interfaces


def add_current_wallet(current_wallet: list[CurrentWallet], session: Session) -> None:
    """Add wallet info to the walletinfo table.

    Arguments
    ---------
    current_wallet: list[CurrentWallet]
        A list of CurrentWallet objects to insert into postgres
    session: Session
        The initialized session object
    """
    for wallet in current_wallet:
        session.add(wallet)
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error on adding wallet_infos: %s", err)
        raise err


def get_current_wallet(
    session: Session,
    end_block: int | None = None,
    wallet_address: list[str] | None = None,
    coerce_float=True,
    raw: bool = False,
) -> pd.DataFrame:
    """Get all current wallet data in history and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    wallet_address: list[str] | None, optional
        The wallet addresses to filter the query on
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal
    raw: bool
        If true, will return the raw data without any adjustments.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    # TODO this function might not scale, as it's looking across all blocks from the beginning of time
    # Ways to improve: add indexes on wallet_address, token_type, block_number

    # Postgres SQL query (this one is fast, but isn't supported by sqlite)
    # select distinct on (wallet_address, token_type) * from CurrentWallet
    # order by block_number DESC;
    # This query selects distinct wallet_address and token_type from current wallets,
    # selecting only the first entry of each group. Since we order each group by descending block_number,
    # this first entry is the latest entry of block_number.

    # Generic SQL query (this one is slow, but is database agnostic)

    query = session.query(CurrentWallet)

    # Support for negative indices
    if end_block is None:
        end_block = get_latest_block_number_from_table(CurrentWallet, session) + 1

    elif end_block < 0:
        end_block = get_latest_block_number_from_table(CurrentWallet, session) + end_block + 1

    if wallet_address is not None:
        query = query.filter(CurrentWallet.wallet_address.in_(wallet_address))

    query = query.filter(CurrentWallet.block_number < end_block)
    query = query.distinct(CurrentWallet.wallet_address, CurrentWallet.token_type)
    query = query.order_by(CurrentWallet.wallet_address, CurrentWallet.token_type, CurrentWallet.block_number.desc())
    current_wallet = pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)
    if raw:
        return current_wallet

    # Rename block_number column to be latest_block_update, and set the new block_number to be the query block
    current_wallet["latest_block_update"] = current_wallet["block_number"]
    current_wallet["block_number"] = end_block - 1

    # Drop id, as id is autofilled when inserting
    current_wallet = current_wallet.drop("id", axis=1)

    # filter non-base zero positions here
    has_value = current_wallet["value"] > 0
    is_base = current_wallet["token_type"] == BASE_TOKEN_SYMBOL

    return current_wallet[has_value | is_base].copy()


def get_pool_analysis(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    return_timestamp: bool = True,
    coerce_float=True,
) -> pd.DataFrame:
    """Get all pool analysis and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    return_timestamp: bool, optional
        Gets timestamps when looking at pool analysis. Defaults to True
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data
    """
    if return_timestamp:
        query = session.query(PoolInfo.timestamp, PoolAnalysis)
    else:
        query = session.query(PoolAnalysis)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(PoolAnalysis, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(PoolAnalysis, session) + end_block + 1

    if start_block is not None:
        query = query.filter(PoolAnalysis.block_number >= start_block)
    if end_block is not None:
        query = query.filter(PoolAnalysis.block_number < end_block)

    if return_timestamp:
        # query from PoolInfo the timestamp
        query = query.join(PoolInfo, PoolAnalysis.block_number == PoolInfo.block_number)

    # Always sort by block in order
    query = query.order_by(PoolAnalysis.block_number)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_ticker(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | None = None,
    max_rows: int | None = None,
    sort_desc: bool | None = False,
    coerce_float=True,
) -> pd.DataFrame:
    """Get all pool analysis and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    wallet_address: list[str] | None, optional
        The wallet addresses to filter the query on
    max_rows: int | None
        The number of rows to return. If None, will return all rows
    sort_desc: bool, optional
        If true, will sort in descending order
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data
    """
    # pylint: disable=too-many-arguments
    query = session.query(Ticker)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(Ticker, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(Ticker, session) + end_block + 1

    if start_block is not None:
        query = query.filter(Ticker.block_number >= start_block)
    if end_block is not None:
        query = query.filter(Ticker.block_number < end_block)

    if wallet_address is not None:
        query = query.filter(Ticker.wallet_address.in_(wallet_address))

    # Always sort by block in order
    # NOTE this affects which results get returned if max_rows is set
    if sort_desc:
        query = query.order_by(Ticker.block_number.desc())
    else:
        query = query.order_by(Ticker.block_number)

    if max_rows is not None:
        query = query.limit(max_rows)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


# Lots of arguments, most are defaults
# pylint: disable=too-many-arguments
def get_wallet_pnl(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | None = None,
    return_timestamp: bool = True,
    coerce_float=True,
) -> pd.DataFrame:
    """Get all wallet pnl and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    wallet_address: list[str] | None, optional
        The wallet addresses to filter the query on. Returns all if None.
    return_timestamp: bool, optional
        Returns the timestamp from the pool info table if True. Defaults to True.
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data
    """
    if return_timestamp:
        query = session.query(PoolInfo.timestamp, WalletPNL)
    else:
        query = session.query(WalletPNL)

    latest_block = get_latest_block_number_from_table(WalletDelta, session)
    if start_block is None:
        start_block = 0
    if end_block is None:
        end_block = latest_block + 1

    # Support for negative indices
    if start_block < 0:
        start_block = latest_block + start_block + 1
    if end_block < 0:
        end_block = latest_block + end_block + 1

    query = query.filter(WalletPNL.block_number >= start_block)
    query = query.filter(WalletPNL.block_number < end_block)
    if wallet_address is not None:
        query = query.filter(WalletPNL.wallet_address.in_(wallet_address))

    if return_timestamp:
        # query from PoolInfo the timestamp
        query = query.join(PoolInfo, WalletPNL.block_number == PoolInfo.block_number)

    # Always sort by block in order
    query = query.order_by(WalletPNL.block_number)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_total_wallet_pnl_over_time(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | None = None,
    coerce_float=True,
) -> pd.DataFrame:
    """Get total pnl across wallets over time and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    wallet_address: list[str] | None, optional
        The wallet addresses to filter the query on. Returns all if None.
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data
    """
    # Do a subquery that groups wallet pnl by address and block
    # Not sure why func.sum is not callable, but it is
    subquery = session.query(
        WalletPNL.wallet_address,
        WalletPNL.block_number,
        func.sum(WalletPNL.pnl).label("pnl"),  # pylint: disable=not-callable
    )

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletPNL, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletPNL, session) + end_block + 1

    if start_block is not None:
        subquery = subquery.filter(WalletPNL.block_number >= start_block)
    if end_block is not None:
        subquery = subquery.filter(WalletPNL.block_number < end_block)
    if wallet_address is not None:
        subquery = subquery.filter(WalletPNL.wallet_address.in_(wallet_address))

    subquery = subquery.group_by(WalletPNL.wallet_address, WalletPNL.block_number)

    # Always sort by block in order
    subquery = subquery.order_by(WalletPNL.block_number).subquery()

    # Additional query to join timestamp to block number
    query = session.query(PoolInfo.timestamp, subquery)
    query = query.join(PoolInfo, subquery.c.block_number == PoolInfo.block_number)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_wallet_positions_over_time(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | None = None,
    coerce_float=True,
) -> pd.DataFrame:
    """Get wallet positions over time and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    wallet_address: list[str] | None, optional
        The wallet addresses to filter the query on. Returns all if None.
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data
    """
    # Not sure why func.sum is not callable, but it is
    subquery = session.query(
        WalletPNL.wallet_address,
        WalletPNL.block_number,
        WalletPNL.base_token_type,
        func.sum(WalletPNL.value).label("value"),  # pylint: disable=not-callable
    )

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletPNL, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletPNL, session) + end_block + 1

    if start_block is not None:
        subquery = subquery.filter(WalletPNL.block_number >= start_block)
    if end_block is not None:
        subquery = subquery.filter(WalletPNL.block_number < end_block)
    if wallet_address is not None:
        subquery = subquery.filter(WalletPNL.wallet_address.in_(wallet_address))

    subquery = subquery.group_by(WalletPNL.wallet_address, WalletPNL.block_number, WalletPNL.base_token_type).subquery()

    # query from PoolInfo the timestamp
    query = session.query(PoolInfo.timestamp, subquery)
    query = query.join(PoolInfo, subquery.c.block_number == PoolInfo.block_number)

    # Always sort by block in order
    query = query.order_by(PoolInfo.timestamp)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)
