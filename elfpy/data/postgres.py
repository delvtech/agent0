"""Initialize Postgres Server"""

from dataclasses import asdict
from datetime import datetime

import sqlalchemy
from fixedpointmath import FixedPoint
from sqlalchemy import Column, DateTime, ForeignKey, Integer, Numeric, String, create_engine, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from elfpy.data.pool_info import PoolInfo

# classes for sqlalchemy that define table schemas have no methods.
# pylint: disable=too-few-public-methods

Base = declarative_base()

# replace the user, password, and db_name with credentials
engine = create_engine("postgresql://admin:password@localhost:5432/postgres_db")


class UserTable(Base):
    """User Schema"""

    __tablename__ = "users"

    # address
    id = Column(String, primary_key=True)


class TransactionTable(Base):
    """Transactions Schema"""

    __tablename__ = "transactions"

    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"))
    amount = Column(Integer)


class PoolInfoTable(Base):
    """PoolInfo Schema"""

    # names are in snake case to indicate values came from solidity
    # pylint: disable=invalid-name

    __tablename__ = "poolinfo"

    # Generate schema from PoolInfo data class
    # These member variables match exactly with the dataclass pool_info

    blockNumber = Column(Integer, primary_key=True)
    # All timestamps are stored without timezone, in UTC.
    timestamp = Column(DateTime, index=True)

    shareReserves = Column(Numeric)
    bondReserves = Column(Numeric)
    lpTotalSupply = Column(Numeric)
    sharePrice = Column(Numeric)
    longsOutstanding = Column(Numeric)
    longAverageMaturityTime = Column(Numeric)
    shortsOutstanding = Column(Numeric)
    shortAverageMaturityTime = Column(Numeric)
    shortBaseVolume = Column(Numeric)
    withdrawalSharesReadyToWithdraw = Column(Numeric)
    withdrawalSharesProceeds = Column(Numeric)


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
        print(f"Adding block {pool_info.blockNumber} to db")
        insert_dict = asdict(pool_info)
        insert_dict["timestamp"] = datetime.fromtimestamp(pool_info.timestamp)
        for key, value in insert_dict.items():
            if isinstance(value, FixedPoint):
                insert_dict[key] = float(value)

        pool_info_entry = PoolInfoTable(**insert_dict)
        session.add(pool_info_entry)

    try:
        session.commit()
    except sqlalchemy.exc.DataError as err:  # type: ignore
        print(f"{pool_infos=}")
        raise err


def get_latest_block_number(session):
    query_results = session.query(PoolInfoTable).order_by(PoolInfoTable.timestamp.desc()).first()
    if query_results is None:
        return 0
    else:
        return int(query_results.blockNumber)
