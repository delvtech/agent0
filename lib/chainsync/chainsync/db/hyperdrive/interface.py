"""Utilities for hyperdrive related postgres interactions."""
from __future__ import annotations

import logging

import pandas as pd
from chainsync.db.base import get_latest_block_number_from_table
from sqlalchemy import exc, func
from sqlalchemy.orm import Session

from .schema import (
    CheckpointInfo,
    CurrentWallet,
    HyperdriveTransaction,
    PoolAnalysis,
    PoolConfig,
    PoolInfo,
    Ticker,
    WalletDelta,
    WalletInfoFromChain,
    WalletPNL,
)


def add_transactions(transactions: list[HyperdriveTransaction], session: Session) -> None:
    """Add transactions to the poolinfo table.

    Arguments
    ---------
    transactions : list[HyperdriveTransaction]
        A list of HyperdriveTransaction objects to insert into postgres
    session : Session
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


def add_wallet_infos(wallet_infos: list[WalletInfoFromChain], session: Session) -> None:
    """Add wallet info to the walletinfo table.

    Arguments
    ---------
    wallet_infos: list[WalletInfo]
        A list of WalletInfo objects to insert into postgres
    session: Session
        The initialized session object
    """
    for wallet_info in wallet_infos:
        session.add(wallet_info)
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error on adding wallet_infos: %s", err)
        raise err


def get_pool_config(session: Session, contract_address: str | None = None, coerce_float=True) -> pd.DataFrame:
    """Get all pool config and returns as a pandas dataframe.

    Arguments
    ---------
    session : Session
        The initialized session object
    contract_address : str | None, optional
        The contract_address to filter the results on. Return all if None

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool config data
    """
    query = session.query(PoolConfig)
    if contract_address is not None:
        query = query.filter(PoolConfig.contractAddress == contract_address)
    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def add_pool_config(pool_config: PoolConfig, session: Session) -> None:
    """Add pool config to the pool config table if not exist.

    Verify pool config if it does exist.

    Arguments
    ---------
    pool_config : PoolConfig
        A PoolConfig object to insert into postgres
    session : Session
        The initialized session object
    """
    # NOTE the logic below is not thread safe, i.e., a race condition can exists
    # if multiple threads try to add pool config at the same time
    # This function is being called by acquire_data.py, which should only have one
    # instance per db, so no need to worry about it here

    # Since we're doing a direct equality comparison, we don't want to coerce into floats here
    existing_pool_config = get_pool_config(session, contract_address=pool_config.contractAddress, coerce_float=False)

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
        # Should never get here, contractAddress is primary_key, which is unique
        raise ValueError


def add_pool_infos(pool_infos: list[PoolInfo], session: Session) -> None:
    """Add a pool info to the poolinfo table.

    Arguments
    ---------
    pool_infos : list[PoolInfo]
        A list of PoolInfo objects to insert into postgres
    session : Session
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


def add_checkpoint_infos(checkpoint_infos: list[CheckpointInfo], session: Session) -> None:
    """Add checkpoint info to the checkpointinfo table.

    Arguments
    ---------
    checkpoint_infos : list[CheckpointInfo]
        A list of CheckpointInfo objects to insert into postgres
    session : Session
        The initialized session object
    """
    for checkpoint_info in checkpoint_infos:
        session.add(checkpoint_info)
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        raise err


def add_wallet_deltas(wallet_deltas: list[WalletDelta], session: Session) -> None:
    """Add wallet deltas to the walletdelta table.

    Arguments
    ---------
    transactions : list[WalletDelta]
        A list of WalletDelta objects to insert into postgres
    session : Session
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
    session : Session
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
    session : Session
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
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    coerce_float : bool
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
        query = query.filter(PoolInfo.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(PoolInfo.blockNumber < end_block)

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
    session : Session
        The initialized session object
    start_block : int | None
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    coerce_float : bool
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
        query = query.filter(HyperdriveTransaction.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(HyperdriveTransaction.blockNumber < end_block)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_checkpoint_info(
    session: Session, start_block: int | None = None, end_block: int | None = None, coerce_float=True
) -> pd.DataFrame:
    """Get all info associated with a given checkpoint.

    This includes
    - `sharePrice` : The share price of the first transaction in the checkpoint.
    - `longSharePrice` : The weighted average of the share prices that all longs in the checkpoint were opened at.
    - `shortBaseVolume` : The aggregate amount of base committed by LPs to pay for bonds sold short in the checkpoint.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    coerce_float : bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried checkpoint info
    """
    query = session.query(CheckpointInfo)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(CheckpointInfo, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(CheckpointInfo, session) + end_block + 1

    if start_block is not None:
        query = query.filter(CheckpointInfo.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(CheckpointInfo.blockNumber < end_block)

    # Always sort by time in order
    query = query.order_by(CheckpointInfo.timestamp)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_all_wallet_info(
    session: Session, start_block: int | None = None, end_block: int | None = None, coerce_float: bool = True
) -> pd.DataFrame:
    """Get all of the wallet_info data in history and returns as a pandas dataframe.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    coerce_float : bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    query = session.query(WalletInfoFromChain)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletInfoFromChain, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletInfoFromChain, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletInfoFromChain.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletInfoFromChain.blockNumber < end_block)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_wallet_info_history(session: Session, coerce_float=True) -> dict[str, pd.DataFrame]:
    """Get the history of all wallet info over block time.

    Arguments
    ---------
    session : Session
        The initialized session object
    coerce_float : bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    dict[str, DataFrame]
        A dictionary keyed by the wallet address, where the values is a DataFrame
        where the index is the block number, and the columns is the number of each
        token the address has at that block number, plus a timestamp and the share price of the block
    """
    # Get data
    all_wallet_info = get_all_wallet_info(session, coerce_float=coerce_float)
    pool_info_lookup = get_pool_info(session, coerce_float=coerce_float)[["timestamp", "sharePrice"]]

    # Pivot tokenType to columns, keeping walletAddress and blockNumber
    all_wallet_info = all_wallet_info.pivot(
        values="tokenValue", index=["walletAddress", "blockNumber"], columns=["tokenType"]
    )
    # Forward fill nan here, as no data means no change
    all_wallet_info = all_wallet_info.fillna(method="ffill")

    # Convert walletAddress to outer dictionary
    wallet_info_dict = {}
    for addr in all_wallet_info.index.get_level_values(0).unique():
        addr_wallet_info = all_wallet_info.loc[addr]
        # Reindex block number to be continuous, filling values with the last entry
        addr_wallet_info = addr_wallet_info.reindex(pool_info_lookup.index, method="ffill")
        addr_wallet_info["timestamp"] = pool_info_lookup.loc[addr_wallet_info.index, "timestamp"]
        addr_wallet_info["sharePrice"] = pool_info_lookup.loc[addr_wallet_info.index, "sharePrice"]
        # Drop all rows where BASE tokens are nan
        addr_wallet_info = addr_wallet_info.dropna(subset="BASE")
        # Fill the rest with 0 values
        addr_wallet_info = addr_wallet_info.fillna(0)
        # Remove name from column index
        addr_wallet_info.columns.name = None
        wallet_info_dict[addr] = addr_wallet_info

    return wallet_info_dict


def get_current_wallet_info(
    session: Session, start_block: int | None = None, end_block: int | None = None, coerce_float: bool = True
) -> pd.DataFrame:
    """Get the balance of a wallet and a given end_block.

    Note
    ----
    Here, you can specify a start_block for performance reasons,
    but if a trade happens before the start_block,
    that token won't show up in the result.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    coerce_float : bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    all_wallet_info = get_all_wallet_info(
        session, start_block=start_block, end_block=end_block, coerce_float=coerce_float
    )
    # Get last entry in the table of each wallet address and token type
    # This should always return a dataframe
    # Pandas doesn't play nice with types
    result = (
        all_wallet_info.sort_values("blockNumber", ascending=False)
        .groupby(["walletAddress", "tokenType"])
        .agg(
            {
                "tokenValue": "first",
                "baseTokenType": "first",
                "maturityTime": "first",
                "blockNumber": "first",
                "sharePrice": "first",
            }
        )
    )
    assert isinstance(result, pd.DataFrame), "result is not a dataframe"
    current_wallet_info: pd.DataFrame = result

    # Rename blockNumber column
    current_wallet_info = current_wallet_info.rename({"blockNumber": "latestUpdateBlock"}, axis=1)
    # Filter current_wallet_info to remove 0 balance tokens
    current_wallet_info = current_wallet_info[current_wallet_info["tokenValue"] > 0]

    return current_wallet_info


def get_wallet_deltas(
    session: Session, start_block: int | None = None, end_block: int | None = None, coerce_float=True
) -> pd.DataFrame:
    """Get all wallet_delta data in history and returns as a pandas dataframe.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    coerce_float : bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    query = session.query(WalletDelta)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletDelta, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletDelta, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletDelta.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletDelta.blockNumber < end_block)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_all_traders(
    session: Session, start_block: int | None = None, end_block: int | None = None, coerce_float=True
) -> list[str]:
    """Get the list of all traders from the WalletInfo table.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    coerce_float : bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    list[str]
        A list of addresses that have made a trade
    """
    query = session.query(WalletDelta.walletAddress)
    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletDelta, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletDelta, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletDelta.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletDelta.blockNumber < end_block)

    if query is None:
        return []
    query = query.distinct()

    results = pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)

    return results["walletAddress"].to_list()


# Analysis schema interfaces


def add_current_wallet(current_wallet: list[CurrentWallet], session: Session) -> None:
    """Add wallet info to the walletinfo table.

    Arguments
    ---------
    wallet_infos: list[WalletInfo]
        A list of WalletInfo objects to insert into postgres
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
    session: Session, end_block: int | None = None, wallet_address: list[str] | None = None, coerce_float=True
) -> pd.DataFrame:
    """Get all current wallet data in history and returns as a pandas dataframe.

    Arguments
    ---------
    session : Session
        The initialized session object
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    wallet_address : list[str] | None, optional
        The wallet addresses to filter the query on
    coerce_float : bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    # TODO this function might not scale, as it's looking across all blocks from the beginning of time
    # Ways to improve: add indexes on walletAddress, tokenType, blockNumber

    # Postgres SQL query (this one is fast, but isn't supported by sqlite)
    # select distinct on (walletAddress, tokenType) * from CurrentWallet
    # order by blockNumber DESC;
    # This query selects distinct walletAddress and tokenType from current wallets,
    # selecting only the first entry of each group. Since we order each group by descending blockNumber,
    # this first entry is the latest entry of blockNumber.

    # Generic SQL query (this one is slow, but is database agnostic)

    query = session.query(CurrentWallet)

    # Support for negative indices
    if end_block is None:
        end_block = get_latest_block_number_from_table(CurrentWallet, session) + 1

    elif end_block < 0:
        end_block = get_latest_block_number_from_table(CurrentWallet, session) + end_block + 1

    if wallet_address is not None:
        query = query.filter(CurrentWallet.walletAddress.in_(wallet_address))

    query = query.filter(CurrentWallet.blockNumber < end_block)
    query = query.distinct(CurrentWallet.walletAddress, CurrentWallet.tokenType)
    query = query.order_by(CurrentWallet.walletAddress, CurrentWallet.tokenType, CurrentWallet.blockNumber.desc())
    current_wallet = pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)

    # Rename blockNumber column to be latest_block_update, and set the new blockNumber to be the query block
    current_wallet["latest_block_update"] = current_wallet["blockNumber"]
    current_wallet["blockNumber"] = end_block - 1

    # Drop id, as id is autofilled when inserting
    current_wallet = current_wallet.drop("id", axis=1)

    # filter non-base zero positions here
    has_value = current_wallet["value"] > 0
    is_base = current_wallet["tokenType"] == "BASE"

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
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    return_timestamp : bool, optional
        Gets timestamps when looking at pool analysis. Defaults to True
    coerce_float : bool
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
        query = query.filter(PoolAnalysis.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(PoolAnalysis.blockNumber < end_block)

    if return_timestamp:
        # query from PoolInfo the timestamp
        query = query.join(PoolInfo, PoolAnalysis.blockNumber == PoolInfo.blockNumber)

    # Always sort by block in order
    query = query.order_by(PoolAnalysis.blockNumber)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_ticker(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | None = None,
    coerce_float=True,
) -> pd.DataFrame:
    """Get all pool analysis and returns as a pandas dataframe.

    Arguments
    ---------
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    wallet_address : list[str] | None, optional
        The wallet addresses to filter the query on
    coerce_float : bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data
    """
    query = session.query(Ticker)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(Ticker, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(Ticker, session) + end_block + 1

    if start_block is not None:
        query = query.filter(Ticker.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(Ticker.blockNumber < end_block)

    if wallet_address is not None:
        query = query.filter(Ticker.walletAddress.in_(wallet_address))

    # Always sort by block in order
    query = query.order_by(Ticker.blockNumber)

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
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    wallet_address : list[str] | None, optional
        The wallet addresses to filter the query on. Returns all if None.
    return_timestamp : bool, optional
        Returns the timestamp from the pool info table if True. Defaults to True.
    coerce_float : bool
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

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletPNL, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletPNL, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletPNL.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletPNL.blockNumber < end_block)
    if wallet_address is not None:
        query = query.filter(WalletPNL.walletAddress.in_(wallet_address))

    if return_timestamp:
        # query from PoolInfo the timestamp
        query = query.join(PoolInfo, WalletPNL.blockNumber == PoolInfo.blockNumber)

    # Always sort by block in order
    query = query.order_by(WalletPNL.blockNumber)

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
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    wallet_address : list[str] | None, optional
        The wallet addresses to filter the query on. Returns all if None.
    coerce_float : bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data
    """
    # Do a subquery that groups wallet pnl by address and block
    # Not sure why func.sum is not callable, but it is
    subquery = session.query(
        WalletPNL.walletAddress,
        WalletPNL.blockNumber,
        func.sum(WalletPNL.pnl).label("pnl"),  # pylint: disable=not-callable
    )

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletPNL, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletPNL, session) + end_block + 1

    if start_block is not None:
        subquery = subquery.filter(WalletPNL.blockNumber >= start_block)
    if end_block is not None:
        subquery = subquery.filter(WalletPNL.blockNumber < end_block)
    if wallet_address is not None:
        subquery = subquery.filter(WalletPNL.walletAddress.in_(wallet_address))

    subquery = subquery.group_by(WalletPNL.walletAddress, WalletPNL.blockNumber)

    # Always sort by block in order
    subquery = subquery.order_by(WalletPNL.blockNumber).subquery()

    # Additional query to join timestamp to block number
    query = session.query(PoolInfo.timestamp, subquery)
    query = query.join(PoolInfo, subquery.c.blockNumber == PoolInfo.blockNumber)

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
    session : Session
        The initialized session object
    start_block : int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    end_block : int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3]
    wallet_address : list[str] | None, optional
        The wallet addresses to filter the query on. Returns all if None.
    coerce_float : bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data
    """
    # Not sure why func.sum is not callable, but it is
    subquery = session.query(
        WalletPNL.walletAddress,
        WalletPNL.blockNumber,
        WalletPNL.baseTokenType,
        func.sum(WalletPNL.value).label("value"),  # pylint: disable=not-callable
    )

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletPNL, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletPNL, session) + end_block + 1

    if start_block is not None:
        subquery = subquery.filter(WalletPNL.blockNumber >= start_block)
    if end_block is not None:
        subquery = subquery.filter(WalletPNL.blockNumber < end_block)
    if wallet_address is not None:
        subquery = subquery.filter(WalletPNL.walletAddress.in_(wallet_address))

    subquery = subquery.group_by(WalletPNL.walletAddress, WalletPNL.blockNumber, WalletPNL.baseTokenType)

    # Always sort by block in order
    subquery = subquery.order_by(WalletPNL.blockNumber).subquery()

    # query from PoolInfo the timestamp
    query = session.query(PoolInfo.timestamp, subquery)
    query = query.join(PoolInfo, subquery.c.blockNumber == PoolInfo.blockNumber)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)
