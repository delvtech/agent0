"""Initialize Postgres Server"""

import sqlalchemy
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from elfpy.data.db_schema import Base, PoolInfo, Transaction

# classes for sqlalchemy that define table schemas have no methods.
# pylint: disable=too-few-public-methods

# replace the user, password, and db_name with credentials
# TODO remove engine as global
engine = create_engine("postgresql://admin:password@localhost:5432/postgres_db")


# class UserTable(Base):
#    """User Schema"""
#
#    __tablename__ = "users"
#
#    # address
#    id = Column(String, primary_key=True)
#
#


def initialize_session():
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


def close_session(session):
    """Close the session"""
    session.close()


def add_pool_infos(pool_infos: list[PoolInfo], session):
    """Add a pool info to the poolinfo table"""

    for pool_info in pool_infos:
        session.add(pool_info)

    try:
        session.commit()
    except sqlalchemy.exc.DataError as err:  # type: ignore
        print(f"{pool_infos=}")
        raise err


def add_transactions(transactions: list[Transaction], session):
    """Add transactions to the poolinfo table"""

    for transaction in transactions:
        session.add(transaction)

    try:
        session.commit()
    except sqlalchemy.exc.DataError as err:  # type: ignore
        print(f"{transactions=}")
        raise err


def get_latest_block_number(session):
    """Gets the latest block number based on the pool info table in the db"""
    # query_results = session.query(PoolInfoTable).order_by(PoolInfoTable.timestamp.desc()).first()
    query_results = session.query(PoolInfo).order_by(PoolInfo.timestamp.desc()).first()
    # If the table is empty, query_results will return None
    if query_results is None:
        return 0
    return int(query_results.blockNumber)
