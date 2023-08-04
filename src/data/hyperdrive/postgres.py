"""Utilities for hyperdrive related postgres interactions."""

from __future__ import annotations

import pandas as pd
from sqlalchemy import exc
from sqlalchemy.orm import Session

from src.data.hyperdrive.agent_position import AgentPosition
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


def get_all_wallet_info(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
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

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    query = session.query(WalletInfo)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletInfo, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletInfo, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletInfo.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletInfo.blockNumber < end_block)

    return pd.read_sql(query.statement, con=session.connection())


def get_wallet_info_history(session: Session) -> dict[str, pd.DataFrame]:
    """Get the history of all wallet info over block time.

    Arguments
    ---------
    session : Session
        The initialized session object

    Returns
    -------
    dict[str, DataFrame]
        A dictionary keyed by the wallet address, where the values is a DataFrame
        where the index is the block number, and the columns is the number of each
        token the address has at that block number, plus a timestamp and the share price of the block
    """
    # Get data
    all_wallet_info = get_all_wallet_info(session)
    pool_info_lookup = get_pool_info(session)[["timestamp", "sharePrice"]]

    # Pivot tokenType to columns, keeping walletAddress and blockNumber
    all_wallet_info = all_wallet_info.pivot(
        values="tokenValue", index=["walletAddress", "blockNumber"], columns=["tokenType"]
    )
    # Forward fill nans here, as no data means no change
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
    session: Session, start_block: int | None = None, end_block: int | None = None
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

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """
    all_wallet_info = get_all_wallet_info(session, start_block=start_block, end_block=end_block)
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


def get_wallet_deltas(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
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

    return pd.read_sql(query.statement, con=session.connection())


def get_agents(session: Session, start_block: int | None = None, end_block: int | None = None) -> list[str]:
    """Get the list of all agents from the WalletInfo table.

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
    list[str]
        A list of agent addresses
    """
    query = session.query(WalletInfo.walletAddress)
    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = get_latest_block_number_from_table(WalletInfo, session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = get_latest_block_number_from_table(WalletInfo, session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletInfo.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletInfo.blockNumber < end_block)

    if query is None:
        return []
    query = query.distinct()

    results = pd.read_sql(query.statement, con=session.connection())

    return results["walletAddress"].to_list()


def get_agent_positions(session: Session, filter_addr: list[str] | None = None) -> dict[str, AgentPosition]:
    """Create an AgentPosition for each agent in the wallet history.

    Arguments
    ---------
    session : Session
        The initialized session object
    filter_addr : list[str] | None
        Only return these addresses. Returns all if None

    Returns
    -------
    dict[str, AgentPosition]
        Returns a dictionary keyed by wallet address, value of an agent's position
    """
    if filter_addr is None:
        return {agent: AgentPosition(wallet) for agent, wallet in get_wallet_info_history(session).items()}
    return {
        agent: AgentPosition(wallet)
        for agent, wallet in get_wallet_info_history(session).items()
        if agent in filter_addr
    }
