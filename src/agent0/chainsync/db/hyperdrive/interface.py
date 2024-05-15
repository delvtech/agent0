"""Utilities for hyperdrive related postgres interactions."""

from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import cast, exc, func
from sqlalchemy.orm import Session

from agent0.chainsync.db.base import get_latest_block_number_from_table

from .schema import FIXED_NUMERIC, CheckpointInfo, PoolAnalysis, PoolConfig, PoolInfo, PositionSnapshot, TradeEvent

# Event Data Ingestion Interface


def add_trade_events(transfer_events: list[TradeEvent], session: Session) -> None:
    """Add transfer events to the transfer events table.

    Arguments
    ---------
    transfer_events: list[HyperdriveTransferEvent]
        A list of HyperdriveTransferEvent objects to insert into postgres.
    session: Session
        The initialized session object.
    """
    for transfer_event in transfer_events:
        session.add(transfer_event)
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error adding transaction: %s", err)
        raise err


def get_latest_block_number_from_trade_event(session: Session, wallet_addr: str | None) -> int:
    """Get the latest block number based on the hyperdrive events table in the db.

    Arguments
    ---------
    session: Session
        The initialized session object.
    wallet_addr: str | None
        The wallet address to filter the results on. Can be None to return latest block number
        regardless of wallet.

    Returns
    -------
    int
        The latest block number in the hyperdrive_events table.
    """

    query = session.query(func.max(TradeEvent.block_number))
    if wallet_addr is not None:
        query = query.filter(TradeEvent.wallet_address == wallet_addr)
    query = query.scalar()

    if query is None:
        return 0
    return int(query)


def get_latest_block_number_from_positions_snapshot_table(session: Session, wallet_addr: str | None) -> int:
    """Get the latest block number based on the positions snapshot table in the db.

    Arguments
    ---------
    session: Session
        The initialized session object.
    wallet_addr: str | None
        The wallet address to filter the results on. Can be None to return latest block number
        regardless of wallet.

    Returns
    -------
    int
        The latest block number in the hyperdrive_events table.
    """

    query = session.query(func.max(PositionSnapshot.block_number))
    if wallet_addr is not None:
        query = query.filter(PositionSnapshot.wallet_address == wallet_addr)
    query = query.scalar()

    if query is None:
        return 0
    return int(query)


def get_trade_events(
    session: Session,
    wallet_addr: str | None = None,
    hyperdrive_address: str | None = None,
    all_token_deltas: bool = True,
    coerce_float=False,
) -> pd.DataFrame:
    """Get all trade events and returns a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized db session object.
    wallet_addr: str | None, optional
        The wallet address to filter the results on. Return all if None.
    hyperdrive_address: str | None, optional
        The hyperdrive address to filter the results on. Returns all if None.
    all_token_deltas: bool
        When removing liquidity that results in withdrawal shares, the events table returns
        two entries for this transaction to keep track of token deltas (one for lp tokens and
        one for withdrawal shares). If this flag is true, will return all entries in the table,
        which is useful for calculating token positions. If false, will drop the duplicate
        withdrawal share entry (useful for returning a ticker).
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried trade events data.
    """
    query = session.query(TradeEvent)
    if wallet_addr is not None:
        query = query.filter(TradeEvent.wallet_address == wallet_addr)
    if hyperdrive_address is not None:
        query = query.filter(TradeEvent.hyperdrive_address == hyperdrive_address)
    if not all_token_deltas:
        # Drop the duplicate events
        query = query.filter(
            ~((TradeEvent.event_type == "removeLiquidity") & (TradeEvent.token_id == "WITHDRAWAL_SHARE"))
        )

    # Always sort by block in order
    query = query.order_by(TradeEvent.block_number)
    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_current_positions(
    session: Session,
    wallet_addr: str | None = None,
    hyperdrive_address: str | None = None,
    query_block: int | None = None,
    coerce_float=False,
) -> pd.DataFrame:
    """Gets all positions for a given wallet address.

    Arguments
    ---------
    session: Session
        The initialized db session object.
    wallet_addr: str
        The wallet address to filter the results on.
    hyperdrive_address: str | None, optional
        The hyperdrive address to filter the results on. Returns all if None.
    query_block: int | None, optional
        The block to get positions for. query_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    coerce_float: bool
        If True, will coerce all numeric columns to float.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data.
    """
    # TODO also accept and filter by hyperdrive address here
    # when we move to multi-pool db support
    query = session.query(
        TradeEvent.hyperdrive_address,
        TradeEvent.wallet_address,
        TradeEvent.token_id,
        # We use max in lieu of a "first" or "last" function in sqlalchemy
        func.max(TradeEvent.token_type).label("token_type"),
        func.max(TradeEvent.maturity_time).label("maturity_time"),
        func.sum(TradeEvent.token_delta).label("balance"),
        # Convert to base here
        # Underlying deltas are negative, so We flip signs here to conform to "value spent in base"
        # We explicitly cast to our defined numeric type to truncate to 18 decimal places.
        -cast(
            func.sum(TradeEvent.base_delta + (TradeEvent.vault_share_delta * TradeEvent.vault_share_price)),
            FIXED_NUMERIC,
        ).label("value_spent_in_base"),
        func.max(TradeEvent.block_number).label("last_balance_update_block"),
    )

    if (query_block is not None) and (query_block < 0):
        query_block = get_latest_block_number_from_table(TradeEvent, session) + query_block + 1

    if query_block is not None:
        query = query.filter(TradeEvent.block_number < query_block)

    if wallet_addr is not None:
        query = query.filter(TradeEvent.wallet_address == wallet_addr)

    if hyperdrive_address is not None:
        query = query.filter(TradeEvent.hyperdrive_address == hyperdrive_address)

    query = query.group_by(TradeEvent.hyperdrive_address, TradeEvent.wallet_address, TradeEvent.token_id)
    out_df = pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)
    # Filter out zero balances
    return out_df[out_df["balance"] != 0].copy()


# Chain To Data Ingestion Interface


def get_pool_config(session: Session, hyperdrive_address: str | None = None, coerce_float=True) -> pd.DataFrame:
    """Get all pool config and returns a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None, optional
        The contract_address to filter the results on. Return all if None.
    coerce_float: bool
        If True, will coerce all numeric columns to float.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool config data.
    """
    query = session.query(PoolConfig)
    if hyperdrive_address is not None:
        query = query.filter(PoolConfig.hyperdrive_address == hyperdrive_address)
    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def add_pool_config(pool_config: PoolConfig, session: Session) -> None:
    """Add pool config to the pool config table if not exist.

    Verify pool config if it does exist.

    Arguments
    ---------
    pool_config: PoolConfig
        A PoolConfig object to insert into postgres.
    session: Session
        The initialized session object.
    """
    # NOTE the logic below is not thread safe, i.e., a race condition can exists
    # if multiple threads try to add pool config at the same time
    # This function is being called by acquire_data.py, which should only have one
    # instance per db, so no need to worry about it here
    # Since we're doing a direct equality comparison, we don't want to coerce into floats here
    existing_pool_config = get_pool_config(
        session, hyperdrive_address=pool_config.hyperdrive_address, coerce_float=False
    )
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
        A list of PoolInfo objects to insert into postgres.
    session: Session
        The initialized session object.
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
        A CheckpointInfo object to insert into postgres.
    session: Session
        The initialized session object.
    """
    # NOTE the logic below is not thread safe, i.e., a race condition can exists
    # if multiple threads try to add checkpoint info at the same time
    # This function is being called by acquire_data.py, which should only have one
    # instance per db, so no need to worry about it here
    # Since we're doing a direct equality comparison, we don't want to coerce into floats here
    existing_checkpoint_info = get_checkpoint_info(
        session, checkpoint_info.hyperdrive_address, checkpoint_info.checkpoint_time, coerce_float=False
    )
    if len(existing_checkpoint_info) == 0:
        # Adding new entry, no checks needed
        pass
    elif len(existing_checkpoint_info) == 1:
        # Verify checkpoint info
        if (checkpoint_info.checkpoint_time != existing_checkpoint_info.loc[0, "checkpoint_time"]) or (
            checkpoint_info.vault_share_price != existing_checkpoint_info.loc[0, "vault_share_price"]
        ):
            raise ValueError("Incoming checkpoint info doesn't match vault_share_price.")
        # Set the id to be the same as existing checkpoint info
        # Pandas doesn't play nice with types
        checkpoint_info.id = int(existing_checkpoint_info.loc[0, "id"])  # type: ignore
    else:
        # Should never get here, checkpoint time is primary_key, which is unique
        raise ValueError

    # This merge adds the row if not exist (keyed by checkpoint_time),
    # otherwise will overwrite with this entry
    session.merge(checkpoint_info, load=True)
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error adding checkpoint info: %s", err)
        raise err


def get_latest_block_number_from_pool_info_table(session: Session) -> int:
    """Get the latest block number based on the pool info table in the db.

    Arguments
    ---------
    session: Session
        The initialized session object.

    Returns
    -------
    int
        The latest block number in the poolinfo table.
    """
    return get_latest_block_number_from_table(PoolInfo, session)


def get_latest_block_number_from_analysis_table(session: Session) -> int:
    """Get the latest block number based on the pool info table in the db.

    Arguments
    ---------
    session: Session
        The initialized session object.

    Returns
    -------
    int
        The latest block number in the poolinfo table.
    """
    return get_latest_block_number_from_table(PoolAnalysis, session)


def get_pool_info(
    session: Session,
    hyperdrive_address: str | None = None,
    start_block: int | None = None,
    end_block: int | None = None,
    coerce_float=True,
) -> pd.DataFrame:
    """Get all pool info and returns a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None, optional
        The hyperdrive address to filter the query on. Return all if None.
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    coerce_float: bool, optional
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data.
    """
    query = session.query(PoolInfo)

    if hyperdrive_address is not None:
        query = query.filter(PoolInfo.hyperdrive_address == hyperdrive_address)

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


def get_checkpoint_info(
    session: Session, hyperdrive_address: str | None = None, checkpoint_time: int | None = None, coerce_float=True
) -> pd.DataFrame:
    """Get all info associated with a given checkpoint.

    This includes
    - `checkpoint_time`: The time index of the checkpoint.
    - `weighted_spot_price`: The time weighted spot price aggregated over the checkpoint.
    - `last_weighted_spot_price_update_time`: The last time the weighted spot price was updated.
    - `vault_share_price`: The share price of the first transaction in the checkpoint.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None, optional
        The hyperdrive pool address to filter the query on. Defaults to returning all checkpoint infos.
    checkpoint_time: int | None, optional
        The checkpoint time to filter the query on. Defaults to returning all checkpoint infos.
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried checkpoint info.
    """
    query = session.query(CheckpointInfo)

    if hyperdrive_address is not None:
        query = query.filter(CheckpointInfo.hyperdrive_address == hyperdrive_address)

    if checkpoint_time is not None:
        query = query.filter(CheckpointInfo.checkpoint_time == checkpoint_time)

    # Always sort by time in order
    query = query.order_by(CheckpointInfo.checkpoint_time)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_all_traders(session: Session, hyperdrive_address: str | None = None) -> pd.Series:
    """Get the list of all traders from the TradeEvent table.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None, optional
        The hyperdrive pool address to filter the query on. Defaults to returning all traders.

    Returns
    -------
    pd.Series
        A list of addresses that have made a trade.
    """
    query = session.query(TradeEvent.wallet_address)
    if hyperdrive_address is not None:
        query = query.filter(CheckpointInfo.hyperdrive_address == hyperdrive_address)
    if query is None:
        return pd.Series([])
    query = query.distinct()

    results = pd.read_sql(query.statement, con=session.connection(), coerce_float=False)

    return results["wallet_address"]


# Analysis schema interfaces


def get_pool_analysis(
    session: Session,
    hyperdrive_address: str | None = None,
    start_block: int | None = None,
    end_block: int | None = None,
    return_timestamp: bool = True,
    coerce_float=True,
) -> pd.DataFrame:
    """Get all pool analysis and returns a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None, optional
        The hyperdrive pool address to filter the query on. Defaults to returning all pool analysis.
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    return_timestamp: bool, optional
        Gets timestamps when looking at pool analysis. Defaults to True.
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data.
    """
    if return_timestamp:
        query = session.query(PoolInfo.timestamp, PoolAnalysis)
    else:
        query = session.query(PoolAnalysis)

    if hyperdrive_address is not None:
        query = query.filter(PoolAnalysis.hyperdrive_address == hyperdrive_address)

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


# Lots of arguments, most are defaults
# pylint: disable=too-many-arguments
def get_position_snapshot(
    session: Session,
    hyperdrive_address: str | None = None,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | str | None = None,
    coerce_float=True,
) -> pd.DataFrame:
    """Get all position snapshot data and returns a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None, optional
        The hyperdrive pool address to filter the query on. Defaults to returning all position snapshots.
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    wallet_address: list[str] | None, optional
        The wallet addresses to filter the query on. Returns all if None.
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data.
    """
    query = session.query(PositionSnapshot)

    if hyperdrive_address is not None:
        query = query.filter(PositionSnapshot.hyperdrive_address == hyperdrive_address)

    latest_block = get_latest_block_number_from_table(PositionSnapshot, session)
    if start_block is None:
        start_block = 0
    if end_block is None:
        end_block = latest_block + 1

    # Support for negative indices
    if start_block < 0:
        start_block = latest_block + start_block + 1
    if end_block < 0:
        end_block = latest_block + end_block + 1

    query = query.filter(PositionSnapshot.block_number >= start_block)
    query = query.filter(PositionSnapshot.block_number < end_block)
    if isinstance(wallet_address, list):
        query = query.filter(PositionSnapshot.wallet_address.in_(wallet_address))
    elif wallet_address is not None:
        query = query.filter(PositionSnapshot.wallet_address == wallet_address)

    # Always sort by block in order
    query = query.order_by(PositionSnapshot.block_number)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_total_pnl_over_time(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | None = None,
    coerce_float=True,
) -> pd.DataFrame:
    """Aggregate pnl over time over all positions a wallet has.

    Arguments
    ---------
    session: Session
        The initialized session object.
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    wallet_address: list[str] | None, optional
        The wallet addresses to filter the query on. Returns all if None.
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data.
    """
    # TODO do we want to keep pools seperate?
    query = session.query(
        PositionSnapshot.wallet_address,
        PositionSnapshot.block_number,
        func.sum(PositionSnapshot.pnl).label("pnl"),
    )

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(PositionSnapshot, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(PositionSnapshot, session) + end_block + 1

    if start_block is not None:
        query = query.filter(PositionSnapshot.block_number >= start_block)
    if end_block is not None:
        query = query.filter(PositionSnapshot.block_number < end_block)
    if wallet_address is not None:
        query = query.filter(PositionSnapshot.wallet_address.in_(wallet_address))

    query = query.group_by(PositionSnapshot.wallet_address, PositionSnapshot.block_number)

    # Always sort by block in order
    query = query.order_by(PositionSnapshot.block_number)

    # TODO add timestamp back in

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_wallet_positions_over_time(
    session: Session,
    hyperdrive_address: str | None = None,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | None = None,
    coerce_float=True,
) -> pd.DataFrame:
    """Get wallet positions over time and returns a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None, optional
        The hyperdrive address to filter the query on. Returns all if None.
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
    wallet_address: list[str] | None, optional
        The wallet addresses to filter the query on. Returns all if None.
    coerce_float: bool
        If true, will return floats in dataframe. Otherwise, will return fixed point Decimal.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data.
    """
    # Not sure why func.sum is not callable, but it is
    subquery = session.query(
        PositionSnapshot.wallet_address,
        PositionSnapshot.block_number,
        PositionSnapshot.token_type,
        func.sum(PositionSnapshot.amount).label("value"),  # pylint: disable=not-callable
    )

    if hyperdrive_address is not None:
        subquery = subquery.filter(PositionSnapshot.hyperdrive_address == hyperdrive_address)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(PositionSnapshot, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(PositionSnapshot, session) + end_block + 1

    if start_block is not None:
        subquery = subquery.filter(PositionSnapshot.block_number >= start_block)
    if end_block is not None:
        subquery = subquery.filter(PositionSnapshot.block_number < end_block)
    if wallet_address is not None:
        subquery = subquery.filter(PositionSnapshot.wallet_address.in_(wallet_address))

    subquery = subquery.group_by(
        PositionSnapshot.wallet_address, PositionSnapshot.block_number, PositionSnapshot.token_type
    ).subquery()

    # query from PoolInfo the timestamp
    query = session.query(PoolInfo.timestamp, subquery)
    query = query.join(PoolInfo, subquery.c.block_number == PoolInfo.block_number)

    # Always sort by block in order
    query = query.order_by(PoolInfo.timestamp)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)
