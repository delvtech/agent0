"""Initialize Postgres Server."""

from __future__ import annotations

import logging
import time
from typing import Type, cast

import pandas as pd
import sqlalchemy
from chainsync import build_postgres_config
from sqlalchemy import URL, Column, Engine, MetaData, String, Table, create_engine, exc, func, inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Session, sessionmaker

from .schema import Base, UserMap

# classes for sqlalchemy that define table schemas have no methods.
# pylint: disable=too-few-public-methods


def query_tables(session: Session) -> list[str]:
    """Return a list of tables in the database.

    Arguments
    ---------
    session : Session
        The initialized session object

    Returns
    -------
    list[str]
        A list of table names in the database
    """
    inspector = inspect(session.bind)  # nice gadget
    assert inspector is not None, "inspector is None"
    return inspector.get_table_names()


def drop_table(session: Session, table_name: str) -> None:
    """Drop a table from the database.

    Arguments
    ---------
    session : Session
        The initialized session object
    table_name : str
        The name of the table to be dropped
    """
    metadata = MetaData()
    table = Table(table_name, metadata)
    bind = session.bind
    assert isinstance(bind, sqlalchemy.engine.base.Engine), "bind is not an engine"
    # checkfirst=true automatically adds an "IF EXISTS" clause
    table.drop(checkfirst=True, bind=bind)


def initialize_engine() -> Engine:
    """Initializes the postgres engine from config

    Returns
    -------
    Engine
        The initialized engine object connected to postgres
    """
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
    exception = None
    for _ in range(10):
        try:
            connection = engine.connect()
            connection.close()
            exception = None
        except OperationalError as ex:
            logging.warning("No connection, retrying")
            exception = ex
            time.sleep(1)
    if exception is not None:
        raise exception
    return engine


def initialize_session() -> Session:
    """Initialize the database if not already initialized.

    Returns
    -------
    session : Session
        The initialized session object
    """

    engine = initialize_engine()
    # create a configured "Session" class
    session_class = sessionmaker(bind=engine)
    # create a session
    session = session_class()
    # create tables
    Base.metadata.create_all(engine)
    # commit the transaction
    session.commit()
    return session


def close_session(session: Session) -> None:
    """Close the session.

    Arguments
    ---------
    session: Session
        The initialized session object
    """
    session.close()


def add_user_map(username: str, addresses: list[str], session: Session) -> None:
    """Add username mapping to postgres during evm_bots initialization.

    Arguments
    ---------
    username : str
        The logical username to attach to the wallet address
    addresses : list[str]
        A list of wallet addresses to map to the username
    session : Session
        The initialized session object
    """
    for address in addresses:
        # Below is a best effort check against the database to see if the address is registered to another username
        # This is best effort because there's a race condition here, e.g.,
        # I read (address_1, user_1), someone else writes (address_1, user_2), I write (address_1, user_1)
        # Because the call below is a `merge`, the final entry in the db is (address_1, user_1).
        existing_user_map = get_user_map(session, address)
        if len(existing_user_map) == 0:
            # Address doesn't exist, all good
            pass
        elif len(existing_user_map) == 1:
            existing_username = existing_user_map.iloc[0]["username"]
            if existing_username != username:
                raise ValueError(f"Wallet {address=} already registered to {existing_username}")
        else:
            # Should never be more than one address in table
            raise ValueError("Fatal error: postgres returning multiple entries for primary key")

        # This merge adds the row if not exist (keyed by address), otherwise will overwrite with this entry
        session.merge(UserMap(address=address, username=username))

    try:
        session.commit()
    except exc.DataError as err:
        logging.error("DB Error adding user: %s", err)
        raise err


def get_user_map(session: Session, address: str | None = None) -> pd.DataFrame:
    """Get all usermapping and returns as a pandas dataframe.

    Arguments
    ---------
    session : Session
        The initialized session object
    address : str | None, optional
        The wallet address to filter the results on. Return all if None

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool config data
    """
    query = session.query(UserMap)
    if address is not None:
        query = query.filter(UserMap.address == address)
    return pd.read_sql(query.statement, con=session.connection())


class TableWithBlockNumber(Base):
    """An abstract table that has blockNumber"""

    __abstract__ = True

    @declared_attr
    # has to be camelCase to match table column name
    # pylint: disable=invalid-name
    def blockNumber(self):
        """Stubbed blockNumber column."""
        return Column(String)


def get_latest_block_number_from_table(table_obj: Type[Base], session: Session) -> int:
    """Get the latest block number based on the specified table in the db.

    Arguments
    ---------
    table_obj : Type[Base]
        The sqlalchemy class that contains the blockNumber column
    session : Session
        The initialized session object

    Returns
    -------
    int
        The latest block number from the specified table
    """

    if not hasattr(table_obj, "blockNumber"):
        raise ValueError("Table does not have a blockNumber column")

    table = cast(TableWithBlockNumber, table_obj)

    # For some reason, pylint doesn't like func.max from sqlalchemy
    result = session.query(func.max(table.blockNumber)).first()  # pylint: disable=not-callable
    # If table doesn't exist
    if result is None:
        return 0
    # If table exists but no data
    if result[0] is None:
        return 0
    return int(result[0])
