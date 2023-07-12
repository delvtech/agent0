"""Initialize Postgres Server"""

from __future__ import annotations

import os
from dataclasses import dataclass

import pandas as pd
import sqlalchemy
from sqlalchemy import URL, create_engine
from sqlalchemy.orm import Session, sessionmaker

from elfpy.data.db_schema import Base, PoolConfig, PoolInfo, Transaction, WalletInfo

# classes for sqlalchemy that define table schemas have no methods.
# pylint: disable=too-few-public-methods

# replace the user, password, and db_name with credentials
# TODO remove engine as global


@dataclass
class PostgresConfig:
    """The configuration dataclass for postgress connections"""

    # default values for local postgres
    # Matching environemnt variables to search for
    # pylint: disable=invalid-name
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "postgres_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432


def build_postgres_config() -> PostgresConfig:
    """Build a PostgresConfig that looks for environmental variables
    If env var exists, use that, otherwise, default
    """
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")

    arg_dict = {}
    if user is not None:
        arg_dict["POSTGRES_USER"] = user
    if password is not None:
        arg_dict["POSTGRES_PASSWORD"] = password
    if database is not None:
        arg_dict["POSTGRES_DB"] = database
    if host is not None:
        arg_dict["POSTGRES_HOST"] = host
    if port is not None:
        arg_dict["POSTGRES_PORT"] = int(port)

    return PostgresConfig(**arg_dict)


def initialize_session() -> Session:
    """Initialize the database if not already initialized"""

    postgres_config = build_postgres_config()

    url_object = URL.create(
        drivername="postgresql",
        username=postgres_config.POSTGRES_USER,
        password=postgres_config.POSTGRES_PASSWORD,
        host=postgres_config.POSTGRES_HOST,
        port=postgres_config.POSTGRES_PORT,
        database=postgres_config.POSTGRES_DB,
    )
    engine = create_engine(url_object)

    # create a configured "Session" class
    session_class = sessionmaker(bind=engine)

    # create a session
    session = session_class()

    # create tables
    Base.metadata.create_all(engine)

    # commit the transaction
    session.commit()

    return session


def close_session(session: Session):
    """Close the session

    Arguments
    ---------
    session: Session
        The initialized session object
    """
    session.close()


def add_wallet_infos(wallet_infos: list[WalletInfo], session: Session):
    """Add wallet info to the walletinfo table
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
    except sqlalchemy.exc.DataError as err:  # type: ignore
        print(f"{wallet_infos=}")
        raise err


def add_pool_config(pool_config: PoolConfig, session: Session):
    """
    Add pool config to the pool config table if not exist
    Verify pool config if it does exist

    Arguments
    ---------
    pool_config: PoolConfig
        A PoolConfig object to insert into postgres
    session: Session
        The initialized session object
    """

    existing_pool_config = get_pool_config(session, contract_address=pool_config.contractAddress)

    if len(existing_pool_config) == 0:
        session.add(pool_config)
        try:
            session.commit()
        except sqlalchemy.exc.DataError as err:  # type: ignore
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


def add_pool_infos(pool_infos: list[PoolInfo], session: Session):
    """Add a pool info to the poolinfo table

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
    except sqlalchemy.exc.DataError as err:  # type: ignore
        print(f"{pool_infos=}")
        raise err


def add_transactions(transactions: list[Transaction], session: Session):
    """Add transactions to the poolinfo table

    Arguments
    ---------
    transactions: list[Transaction]
        A list of Transaction objects to insert into postgres
    session: Session
        The initialized session object
    """
    for transaction in transactions:
        session.add(transaction)
    try:
        session.commit()
    except sqlalchemy.exc.DataError as err:  # type: ignore
        print(f"{transactions=}")
        raise err


def get_pool_config(session: Session, contract_address: str | None = None) -> pd.DataFrame:
    """
    Gets all pool config and returns as a pandas dataframe

    Arguments
    ---------
    session: Session
        The initialized session object
    contract_address: str | None
        The contract_address to filter the results on. Return all if None

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool config data
    """
    query = session.query(PoolConfig)
    if contract_address is not None:
        query = query.filter(PoolConfig.contractAddress == contract_address)
    return pd.read_sql(query.statement, con=session.connection())


def get_pool_info(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
    """
    Gets all pool info and returns as a pandas dataframe

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

    return pd.read_sql(query.statement, con=session.connection())


def get_transactions(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
    """
    Gets all transactions and returns as a pandas dataframe

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

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried transactions data
    """

    query = session.query(Transaction)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = _get_latest_block_number_transactions(session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = _get_latest_block_number_transactions(session) + end_block + 1

    if start_block is not None:
        query = query.filter(Transaction.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(Transaction.blockNumber < end_block)

    return pd.read_sql(query.statement, con=session.connection())


def get_all_wallet_info(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
    """
    Gets all of the wallet_info data in history and returns as a pandas dataframe

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

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """

    query = session.query(WalletInfo)

    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = _get_latest_block_number_wallet_info(session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = _get_latest_block_number_wallet_info(session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletInfo.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletInfo.blockNumber < end_block)

    return pd.read_sql(query.statement, con=session.connection())


def get_current_wallet_info(
    session: Session, start_block: int | None = None, end_block: int | None = None
) -> pd.DataFrame:
    """Gets the balance of a wallet and a given end_block
    Here, you can specify a start_block for performance reasons, but if a trade happens before the start_block,
    that token won't show up in the result.

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

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried wallet info data
    """

    all_wallet_info = get_all_wallet_info(session, start_block=start_block, end_block=end_block)
    # Get last entry in the table of each wallet address and token type
    # This should always return a dataframe
    # Pandas doesn't play nice with types
    current_wallet_info: pd.DataFrame = (
        all_wallet_info.sort_values("blockNumber", ascending=False)
        .groupby(["walletAddress", "tokenType"])
        .agg({"tokenValue": "first", "baseTokenType": "first", "maturityTime": "first", "blockNumber": "first"})
    )  # type: ignore

    # Rename blockNumber column
    current_wallet_info = current_wallet_info.rename({"blockNumber": "latestUpdateBlock"}, axis=1)
    # Filter current_wallet_info to remove 0 balance tokens
    current_wallet_info = current_wallet_info[current_wallet_info["tokenValue"] > 0]

    return current_wallet_info


def get_agents(session: Session, start_block: int | None = None, end_block: int | None = None) -> list[str]:
    """Gets the list of all agents from the WalletInfo table"""
    query = session.query(WalletInfo.walletAddress)
    # Support for negative indices
    if (start_block is not None) and (start_block < 0):
        start_block = _get_latest_block_number_wallet_info(session) + start_block + 1
    if (end_block is not None) and (end_block < 0):
        end_block = _get_latest_block_number_wallet_info(session) + end_block + 1

    if start_block is not None:
        query = query.filter(WalletInfo.blockNumber >= start_block)
    if end_block is not None:
        query = query.filter(WalletInfo.blockNumber < end_block)

    if query is None:
        return []
    # TODO test return when empty table
    query = query.distinct()

    results = pd.read_sql(query.statement, con=session.connection())

    return results["walletAddress"].to_list()


def get_latest_block_number(session: Session) -> int:
    """Gets the latest block number based on the pool info table in the db
    Arguments
    ---------
    session: Session
        The initialized session object

    Returns
    -------
    int
        The latest block number in the poolinfo table
    """

    # query_results = session.query(PoolInfoTable).order_by(PoolInfoTable.timestamp.desc()).first()
    query_results = session.query(PoolInfo).order_by(PoolInfo.timestamp.desc()).first()
    # If the table is empty, query_results will return None
    if query_results is None:
        return 0
    return int(query_results.blockNumber)


def _get_latest_block_number_wallet_info(session: Session) -> int:
    """
    Gets the latest block number based on the walletinfo table in the db
    This function shouldn't be called externally, as the pool info table should be the main keeper of block numbers
    """
    query_results = session.query(WalletInfo).order_by(WalletInfo.id.desc()).first()
    # If the table is empty, query_results will return None
    if query_results is None:
        return 0
    return int(query_results.blockNumber)


def _get_latest_block_number_transactions(session: Session) -> int:
    """
    Gets the latest block number based on the transactions table in the db
    This function shouldn't be called externally, as the pool info table should be the main keeper of block numbers
    """
    query_results = session.query(Transaction).order_by(Transaction.id.desc()).first()
    # If the table is empty, query_results will return None
    if query_results is None:
        return 0
    return int(query_results.blockNumber)
