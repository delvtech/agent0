"""Initialize Postgres Server"""

from __future__ import annotations

import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from elfpy.data.db_schema import Base, PoolConfig, PoolInfo, Transaction

# classes for sqlalchemy that define table schemas have no methods.
# pylint: disable=too-few-public-methods

# replace the user, password, and db_name with credentials
# TODO remove engine as global
engine = create_engine("postgresql://admin:password@localhost:5432/postgres_db")


# TODO figure out what this table is supposed to hold
# class UserTable(Base):
#    """User Schema"""
#
#    __tablename__ = "users"
#
#    # address
#    id = Column(String, primary_key=True)
#
#


def initialize_session() -> Session:
    """Initialize the database if not already initialized"""

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
    """Close the session"""
    session.close()


def add_pool_config(pool_config: PoolConfig, session: Session):
    """
    Add pool config to the pool config table if not exist
    Verify pool config if it does exist
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
    """Add a pool info to the poolinfo table"""
    for pool_info in pool_infos:
        session.add(pool_info)
    try:
        session.commit()
    except sqlalchemy.exc.DataError as err:  # type: ignore
        print(f"{pool_infos=}")
        raise err


def add_transactions(transactions: list[Transaction], session: Session):
    """Add transactions to the poolinfo table"""
    for transaction in transactions:
        session.add(transaction)
    try:
        session.commit()
    except sqlalchemy.exc.DataError as err:  # type: ignore
        print(f"{transactions=}")
        raise err


def get_pool_config(session: Session, contract_address: str | None = None) -> pd.DataFrame:
    """
    Gets all pool info and returns as a pandas dataframe
    start_block and end_block match slicing notation, e.g., list[:3] or list[:-3]
    """
    query = session.query(PoolConfig)
    if contract_address is not None:
        query = query.filter(PoolConfig.contractAddress == contract_address)
    return pd.read_sql(query.statement, con=session.connection())


def get_pool_info(session: Session, start_block: int | None = None, end_block: int | None = None) -> pd.DataFrame:
    """
    Gets all pool info and returns as a pandas dataframe
    start_block and end_block match slicing notation, e.g., list[:3] or list[:-3]
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
    start_block and end_block match slicing notation, e.g., list[:3] or list[:-3]
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


def _get_latest_block_number_transactions(session: Session) -> int:
    """
    Gets the latest block number based on the transactions table in the db
    This function shouldn't be called externally, as the pool info table should be the main keeper of block numbers
    This is simply here to query transactions on blocks
    """
    query_results = session.query(Transaction).order_by(Transaction.id.desc()).first()
    # If the table is empty, query_results will return None
    if query_results is None:
        return 0
    return int(query_results.blockNumber)


def get_latest_block_number(session: Session) -> int:
    """Gets the latest block number based on the pool info table in the db"""
    # query_results = session.query(PoolInfoTable).order_by(PoolInfoTable.timestamp.desc()).first()
    query_results = session.query(PoolInfo).order_by(PoolInfo.timestamp.desc()).first()
    # If the table is empty, query_results will return None
    if query_results is None:
        return 0
    return int(query_results.blockNumber)
