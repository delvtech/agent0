import pandas as pd
from sqlalchemy import exc
from sqlalchemy.orm import Session

from src.data.hyperdrive.db_schema import CheckpointInfo, PoolConfig, PoolInfo, WalletDelta, WalletInfo
from src.data.postgres import get_latest_block_number, get_latest_block_number_from_table


def add_wallet_infos(wallet_infos: list[WalletInfo], session: Session) -> None:
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
        print(f"{wallet_infos=}")
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
            print(f"{pool_config=}")
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
        print(f"{pool_infos=}")
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
        print(f"{wallet_deltas=}")
        raise err


def get_pool_info(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
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

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool info data
    """
    query = session.query(PoolInfo)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number(session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number(session) + end_block + 1

    if start_block is not None:
        query = query.filter(PoolInfo.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(PoolInfo.blockNumber < end_block)

    # Always sort by time in order
    query = query.order_by(PoolInfo.timestamp)

    return pd.read_sql(query.statement, con=session.connection()).set_index("blockNumber")


def get_checkpoint_info(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
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

    return pd.read_sql(query.statement, con=session.connection()).set_index("blockNumber")
