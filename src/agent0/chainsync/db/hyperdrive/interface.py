"""Utilities for hyperdrive related postgres interactions."""

from __future__ import annotations

import logging

import pandas as pd
from sqlalchemy import cast, exc, func
from sqlalchemy.orm import Session

from agent0.chainsync.db.base import get_latest_block_number_from_table

from .schema import (
    FIXED_NUMERIC,
    CheckpointInfo,
    HyperdriveAddrToName,
    PoolConfig,
    PoolInfo,
    PositionSnapshot,
    TradeEvent,
)


# Pool Addr Mapping Name
def add_hyperdrive_addr_to_name(
    name: str, hyperdrive_address: str, session: Session, force_update: bool = False
) -> None:
    """Add username mapping to postgres during agent initialization.

    Arguments
    ---------
    name: str
        The logical name to attach to the wallet address.
    hyperdrive_address: str
        A hyperdrive address to map to the name.
    session: Session
        The initialized session object.
    force_update: bool
        If true and an existing mapping is found, will overwrite.
    """
    # Below is a best effort check against the database to see if the address is registered to another name.
    # This is best effort because there's a race condition here, e.g.,
    # I read (address_1, name_1), someone else writes (address_1, name_2), I write (address_1, name_1)
    # Because the call below is a `merge`, the final entry in the db is (address_1, name_1).
    existing_map = get_hyperdrive_addr_to_name(session, hyperdrive_address)
    if len(existing_map) == 0:
        # Address doesn't exist, all good
        pass
    elif len(existing_map) == 1:
        existing_name = existing_map.iloc[0]["name"]
        if existing_name != name and not force_update:
            raise ValueError(
                f"Registering address {hyperdrive_address=} to {name} failed: already registered to {existing_name}"
            )
    else:
        # Should never be more than one address in table
        raise ValueError("Fatal error: postgres returning multiple entries for primary key")

    # This merge adds the row if not exist (keyed by address), otherwise will overwrite with this entry
    session.merge(HyperdriveAddrToName(hyperdrive_address=hyperdrive_address, name=name))

    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("DB Error adding user: %s", err)
        raise err


def get_hyperdrive_addr_to_name(session: Session, hyperdrive_address: str | None = None) -> pd.DataFrame:
    """Get all usermapping and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    hyperdrive_address: str | None, optional
        The hyperdrive address to filter the results on. Return all if None

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool config data
    """
    query = session.query(HyperdriveAddrToName)
    if hyperdrive_address is not None:
        query = query.filter(HyperdriveAddrToName.hyperdrive_address == hyperdrive_address)
    return pd.read_sql(query.statement, con=session.connection())


# Event Data Ingestion Interface


def add_trade_events(transfer_events: list[TradeEvent], session: Session) -> None:
    """Add transfer events to the transfer events table.

    This function is only used for injecting rows into the db.
    The actual ingestion happens via `trade_events_to_db` using dataframes.

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


def get_latest_block_number_from_trade_event(
    session: Session,
    hyperdrive_address: str | None,
    wallet_address: str | None,
) -> int:
    """Get the latest block number based on the hyperdrive events table in the db.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None
        The hyperdrive address to filter the results on. Can be None to return latest block number
        regardless of pool.
    wallet_address: str | None
        The wallet address to filter the results on. Can be None to return latest block number
        regardless of wallet.

    Returns
    -------
    int
        The latest block number in the hyperdrive_events table.
    """

    query = session.query(func.max(TradeEvent.block_number))
    if wallet_address is not None:
        query = query.filter(TradeEvent.wallet_address == wallet_address)
    if hyperdrive_address is not None:
        query = query.filter(TradeEvent.hyperdrive_address == hyperdrive_address)
    query = query.scalar()

    if query is None:
        return 0
    return int(query)


def get_latest_block_number_from_positions_snapshot_table(
    session: Session, wallet_addr: str | None, hyperdrive_address: str | None
) -> int:
    """Get the latest block number based on the positions snapshot table in the db.

    Arguments
    ---------
    session: Session
        The initialized session object.
    wallet_addr: str | None
        The wallet address to filter the results on. Can be None to return latest block number
        regardless of wallet.
    hyperdrive_address: str | None
        The hyperdrive address to filter the results on. Can be None to return latest block number
        regardless of pool.

    Returns
    -------
    int
        The latest block number in the hyperdrive_events table.
    """

    query = session.query(func.max(PositionSnapshot.block_number))
    if wallet_addr is not None:
        query = query.filter(PositionSnapshot.wallet_address == wallet_addr)
    if hyperdrive_address is not None:
        query = query.filter(PositionSnapshot.hyperdrive_address == hyperdrive_address)
    query = query.scalar()

    if query is None:
        return 0
    return int(query)


def get_trade_events(
    session: Session,
    wallet_address: str | list[str] | None = None,
    hyperdrive_address: str | list[str] | None = None,
    all_token_deltas: bool = True,
    sort_ascending: bool = True,
    query_limit: int | None = None,
    coerce_float=False,
) -> pd.DataFrame:
    """Get all trade events and returns a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized db session object.
    wallet_address: str | list[str] | None, optional
        The wallet address(es) to filter the results on. Return all if None.
    hyperdrive_address: str | list[str] | None, optional
        The hyperdrive address(es) to filter the results on. Returns all if None.
    all_token_deltas: bool, optional
        When removing liquidity that results in withdrawal shares, the events table returns
        two entries for this transaction to keep track of token deltas (one for lp tokens and
        one for withdrawal shares). If this flag is True, will return all entries in the table,
        which is useful for calculating token positions. If False, will drop the duplicate
        withdrawal share entry (useful for returning a ticker). Defaults to True.
    sort_ascending: bool, optional
        If True, will sort events in ascending block order. Otherwise, will sort in descending order.
        Defaults to True.
    query_limit: int | None, optional
        The number of rows to return. Defaults to return all rows.
    coerce_float: bool, optional
        If True, will return floats in dataframe. Otherwise, will return fixed point Decimal.
        Defaults to False.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried trade events data.
    """
    # pylint: disable=too-many-arguments

    query = session.query(TradeEvent)

    if isinstance(wallet_address, list):
        query = query.filter(TradeEvent.wallet_address.in_(wallet_address))
    elif wallet_address is not None:
        query = query.filter(TradeEvent.wallet_address == wallet_address)

    if isinstance(hyperdrive_address, list):
        query = query.filter(TradeEvent.hyperdrive_address.in_(hyperdrive_address))
    elif hyperdrive_address is not None:
        query = query.filter(TradeEvent.hyperdrive_address == hyperdrive_address)

    if not all_token_deltas:
        # Drop the duplicate events
        query = query.filter(
            ~((TradeEvent.event_type == "RemoveLiquidity") & (TradeEvent.token_id == "WITHDRAWAL_SHARE"))
        )

    # Always sort by block in order
    if sort_ascending:
        query = query.order_by(TradeEvent.block_number)
    else:
        query = query.order_by(TradeEvent.block_number.desc())

    if query_limit is not None:
        query = query.limit(query_limit)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_current_positions(
    session: Session,
    wallet_addr: str | None = None,
    hyperdrive_address: str | None = None,
    query_block: int | None = None,
    show_closed_positions: bool = False,
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
    show_closed_positions: bool, optional
        Whether to show positions closed positions (i.e., positions with zero balance). Defaults to False.
        When False, will only return currently open positions. Useful for gathering currently open positions.
        When True, will also return any closed positions. Useful for calculating overall pnl of all positions.
    coerce_float: bool
        If True, will coerce all numeric columns to float.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data.
    """
    # pylint: disable=too-many-arguments

    query = session.query(
        TradeEvent.hyperdrive_address,
        TradeEvent.wallet_address,
        TradeEvent.token_id,
        # We use max in lieu of a "first" or "last" function in sqlalchemy
        func.max(TradeEvent.token_type).label("token_type"),
        func.max(TradeEvent.maturity_time).label("maturity_time"),
        func.sum(TradeEvent.token_delta).label("token_balance"),
        # Convert to base here
        # We explicitly cast to our defined numeric type to truncate to 18 decimal places.
        cast(
            func.sum(TradeEvent.base_delta + (TradeEvent.vault_share_delta * TradeEvent.vault_share_price)),
            FIXED_NUMERIC,
        ).label("realized_value"),
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
    if not show_closed_positions:
        out_df = out_df[out_df["token_balance"] != 0].reset_index(drop=True).copy()
    return out_df


# Chain To Data Ingestion Interface


def get_pool_config(session: Session, hyperdrive_address: str | None = None, coerce_float=False) -> pd.DataFrame:
    """Get all pool config and returns a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None, optional
        The contract_address to filter the results on. Return all if None. Defaults to returning all.
    coerce_float: bool, optional
        If True, will coerce all numeric columns to float. Defaults to False.

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

    This function is only used for injecting rows into the db.
    The actual ingestion happens via `checkpoint_events_to_db` using dataframes.

    Arguments
    ---------
    checkpoint_info: CheckpointInfo
        A CheckpointInfo object to insert into postgres.
    session: Session
        The initialized session object.
    """

    session.add(checkpoint_info)
    try:
        session.commit()
    except exc.DataError as err:
        session.rollback()
        logging.error("Error adding transaction: %s", err)
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


def get_pool_info(
    session: Session,
    hyperdrive_address: str | None = None,
    start_block: int | None = None,
    end_block: int | None = None,
    coerce_float=False,
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


def get_latest_block_number_from_checkpoint_info_table(session: Session, hyperdrive_address: str | None) -> int:
    """Get the latest block number based on the checkpoint info table in the db.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None
        The hyperdrive pool address to filter the query on.

    Returns
    -------
    int
        The latest block number in the poolinfo table.
    """
    query = session.query(func.max(CheckpointInfo.block_number))
    if hyperdrive_address is not None:
        query = query.filter(CheckpointInfo.hyperdrive_address == hyperdrive_address)
    query = query.scalar()

    if query is None:
        return 0
    return int(query)


def get_checkpoint_info(
    session: Session, hyperdrive_address: str | None = None, checkpoint_time: int | None = None, coerce_float=False
) -> pd.DataFrame:
    """Get all info associated with a given checkpoint.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | None, optional
        The hyperdrive pool address to filter the query on. Defaults to returning all checkpoint infos.
    checkpoint_time: int | None, optional
        The checkpoint time to filter the query on. Defaults to returning all checkpoint infos.
    coerce_float: bool, optional
        If True, will return floats in dataframe. Otherwise, will return fixed point Decimal.
        Defaults to False

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

    # TODO there exists a race condition where the same checkpoint info row
    # can be duplicated. While this should be fixed in insertion, we fix by
    # ensuring the getter selects on distinct checkpoint times.
    query = query.distinct(CheckpointInfo.hyperdrive_address, CheckpointInfo.checkpoint_time)

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
        query = query.filter(TradeEvent.hyperdrive_address == hyperdrive_address)
    if query is None:
        return pd.Series([])
    query = query.distinct()

    results = pd.read_sql(query.statement, con=session.connection(), coerce_float=False)

    return results["wallet_address"]


# Analysis schema interfaces


# Lots of arguments, most are defaults
# pylint: disable=too-many-arguments
def get_position_snapshot(
    session: Session,
    hyperdrive_address: str | list[str] | None = None,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | str | None = None,
    coerce_float=False,
) -> pd.DataFrame:
    """Get all position snapshot data and returns a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object.
    hyperdrive_address: str | list[str] | None, optional
        The hyperdrive pool address(es) to filter the query on. Defaults to returning all position snapshots.
    start_block: int | None, optional
        The starting block to filter the query on. start_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
        Defaults to first entry.
    end_block: int | None, optional
        The ending block to filter the query on. end_block integers
        matches python slicing notation, e.g., list[:3], list[:-3].
        Defaults to last entry.
    wallet_address: list[str] | None, optional
        The wallet addresses to filter the query on. Returns all if None.
    coerce_float: bool, optional
        If True, will return floats in dataframe. Otherwise, will return fixed point Decimal.
        Defaults to False.

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data.
    """
    query = session.query(PositionSnapshot)

    if isinstance(hyperdrive_address, list):
        query = query.filter(PositionSnapshot.hyperdrive_address.in_(hyperdrive_address))
    elif hyperdrive_address is not None:
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
    coerce_float=False,
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
    # TODO add optional argument of hyperdrive address to not aggregate across pools.
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

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_positions_over_time(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | None = None,
    coerce_float=False,
) -> pd.DataFrame:
    """Aggregate over token types over all position types.

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
    query = session.query(
        PositionSnapshot.wallet_address,
        PositionSnapshot.block_number,
        PositionSnapshot.token_type,
        func.sum(PositionSnapshot.token_balance).label("token_balance"),
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

    query = query.group_by(PositionSnapshot.wallet_address, PositionSnapshot.block_number, PositionSnapshot.token_type)

    # Always sort by block in order
    query = query.order_by(PositionSnapshot.block_number)

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)


def get_realized_value_over_time(
    session: Session,
    start_block: int | None = None,
    end_block: int | None = None,
    wallet_address: list[str] | None = None,
    coerce_float=False,
) -> pd.DataFrame:
    """Aggregate over realized value over all position types.

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
    query = session.query(
        PositionSnapshot.wallet_address,
        PositionSnapshot.block_number,
        func.sum(PositionSnapshot.realized_value).label("realized_value"),
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

    return pd.read_sql(query.statement, con=session.connection(), coerce_float=coerce_float)
