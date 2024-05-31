"""Initialize Postgres Server."""

from __future__ import annotations

import logging
import time
from typing import Type, cast

import pandas as pd
import sqlalchemy
from sqlalchemy import Column, Engine, MetaData, String, Table, create_engine, exc, func, inspect
from sqlalchemy.exc import OperationalError
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.sql import text
from sqlalchemy_utils import create_database, database_exists

from agent0.chainsync import PostgresConfig, build_postgres_config_from_env

from .schema import AddrToUsername, Base

# classes for sqlalchemy that define table schemas have no methods.
# pylint: disable=too-few-public-methods


def query_tables(session: Session) -> list[str]:
    """Return a list of tables in the database.

    Arguments
    ---------
    session: Session
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
    session: Session
        The initialized session object
    table_name: str
        The name of the table to be dropped
    """
    metadata = MetaData()
    table = Table(table_name, metadata)
    bind = session.bind
    assert isinstance(bind, sqlalchemy.engine.base.Engine), "bind is not an engine"
    # checkfirst=true automatically adds an "IF EXISTS" clause
    table.drop(checkfirst=True, bind=bind)


def initialize_engine(postgres_config: PostgresConfig | None = None, ensure_database_created: bool = False) -> Engine:
    """Initialize the postgres engine from config.

    Arguments
    ---------
    postgres_config: PostgresConfig | None, optional
        The postgres config. If none, will set from `.env` file or set to defaults.
    ensure_database_created: bool, optional
        If true, will create the database within postgres if it doesn't exist. Defaults to false.

    Returns
    -------
    Engine
        The initialized engine object connected to postgres
    """
    if postgres_config is None:
        postgres_config = build_postgres_config_from_env()

    url_object = postgres_config.create_url_obj()
    engine = create_engine(url_object)

    if ensure_database_created:
        exception = None
        for _ in range(10):
            try:
                if not database_exists(engine.url):
                    logging.info("Database %s does not exist, creating", postgres_config.POSTGRES_DB)
                    create_database(engine.url)
                exception = None
                break
            except OperationalError as ex:
                logging.warning("No postgres connection, retrying")
                exception = ex
                time.sleep(1)
        if exception is not None:
            raise exception

    exception = None
    for _ in range(10):
        try:
            connection = engine.connect()
            connection.close()
            exception = None
            break
        except OperationalError as ex:
            logging.warning("No postgres connection, retrying")
            exception = ex
            time.sleep(1)
    if exception is not None:
        raise exception

    return engine


def initialize_session(
    postgres_config: PostgresConfig | None = None, drop: bool = False, ensure_database_created: bool = False
) -> Session:
    """Initialize the postgres session.

    Arguments
    ---------
    postgres_config: PostgresConfig | None, optional
        The postgres config. If none, will set from `.env` file or set to defaults.
    drop: bool, optional
        If true, will drop all tables in the database before doing anything for debugging.
        Defaults to false.
    ensure_database_created: bool, optional
        If true, will create the database within postgres if it doesn't exist. Defaults to false.

    Returns
    -------
    Session
        The initialized session object
    """
    engine = initialize_engine(postgres_config, ensure_database_created)

    # create a configured "Session" class
    session_class = sessionmaker(bind=engine)
    # create a session
    session = session_class()
    if drop:
        # Executing raw sql since sqlalchemy can't drop all with cascade
        metadata = MetaData()
        metadata.reflect(engine)
        all_tables = metadata.tables.keys()
        with engine.connect() as conn:
            for table in all_tables:
                drop_query = text(f"DROP TABLE IF EXISTS {table} CASCADE;")
                conn.execute(drop_query)
            conn.commit()

    # There sometimes is a race condition here between data and analysis, keep trying until successful
    exception = None
    for _ in range(10):
        try:
            # create tables
            Base.metadata.create_all(engine)
            # commit the transaction
            session.commit()
            exception = None
            break
        # Catching general exception for retry, will throw if it keeps happening
        # pylint: disable=broad-except
        except Exception as ex:
            logging.warning("Error creating tables, retrying")
            exception = ex
            time.sleep(1)

    if exception is not None:
        raise exception

    return session


def close_session(session: Session) -> None:
    """Close the session.

    Arguments
    ---------
    session: Session
        The initialized session object
    """
    session.close()


def add_addr_to_username(
    username: str, addresses: list[str] | str, session: Session, user_suffix: str = "", force_update: bool = False
) -> None:
    """Add username mapping to postgres during agent initialization.

    Arguments
    ---------
    username: str
        The logical username to attach to the wallet address.
    addresses: list[str] | str
        A single or list of wallet addresses to map to the username.
    session: Session
        The initialized session object.
    user_suffix: str
        An optional suffix to add to the username mapping.
    force_update: bool
        If true and an existing mapping is found, will overwrite.
    """
    if isinstance(addresses, str):
        addresses = [addresses]
    username = username + user_suffix

    for address in addresses:
        # Below is a best effort check against the database to see if the address is registered to another username
        # This is best effort because there's a race condition here, e.g.,
        # I read (address_1, user_1), someone else writes (address_1, user_2), I write (address_1, user_1)
        # Because the call below is a `merge`, the final entry in the db is (address_1, user_1).
        existing_user_map = get_addr_to_username(session, address)
        if len(existing_user_map) == 0:
            # Address doesn't exist, all good
            pass
        elif len(existing_user_map) == 1:
            existing_username = existing_user_map.iloc[0]["username"]
            if existing_username != username and not force_update:
                raise ValueError(f"Wallet {address=} already registered to {existing_username}")
        else:
            # Should never be more than one address in table
            raise ValueError("Fatal error: postgres returning multiple entries for primary key")

        # This merge adds the row if not exist (keyed by address), otherwise will overwrite with this entry
        session.merge(AddrToUsername(address=address, username=username))

    try:
        session.commit()
    except exc.DataError as err:
        logging.error("DB Error adding user: %s", err)
        raise err


def get_addr_to_username(session: Session, address: str | None = None) -> pd.DataFrame:
    """Get all usermapping and returns as a pandas dataframe.

    Arguments
    ---------
    session: Session
        The initialized session object
    address: str | None, optional
        The wallet address to filter the results on. Return all if None

    Returns
    -------
    DataFrame
        A DataFrame that consists of the queried pool config data
    """
    query = session.query(AddrToUsername)
    if address is not None:
        query = query.filter(AddrToUsername.address == address)
    return pd.read_sql(query.statement, con=session.connection())


class TableWithBlockNumber(Base):
    """An abstract table that has block_number"""

    __abstract__ = True

    @declared_attr
    def block_number(self) -> Column:
        """Stubbed block_number column.

        Returns
        -------
        Column
            The sqlalchemy Column object for the block number
        """
        return Column(String)


def get_latest_block_number_from_table(table_obj: Type[Base], session: Session) -> int:
    """Get the latest block number based on the specified table in the db.

    Arguments
    ---------
    table_obj: Type[Base]
        The sqlalchemy class that contains the block_number column
    session: Session
        The initialized session object

    Returns
    -------
    int
        The latest block number from the specified table
    """
    if not hasattr(table_obj, "block_number"):
        raise ValueError("Table does not have a block_number column")

    table = cast(TableWithBlockNumber, table_obj)

    # For some reason, pylint doesn't like func.max from sqlalchemy
    result = session.query(func.max(table.block_number)).first()  # pylint: disable=not-callable
    # If table doesn't exist
    if result is None:
        return 0
    # If table exists but no data
    if result[0] is None:
        return 0
    return int(result[0])
