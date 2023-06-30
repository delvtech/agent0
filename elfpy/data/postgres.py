"""Initialize Postgres Server"""

import sqlalchemy
from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
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

    blockNumber = Column(Integer, primary_key=True)
    timeStamp = Column(Integer, index=True)

    # strings must be used to store uint256 values.
    amount = Column(String)
    shareReserves = Column(String)
    bondReserves = Column(String)
    lpTotalSupply = Column(String)
    sharePrice = Column(String)
    longsOutstanding = Column(String)
    longAverageMaturityTime = Column(String)
    shortsOutstanding = Column(String)
    shortAverageMaturityTime = Column(String)
    shortBaseVolume = Column(String)
    withdrawalSharesReadyToWithdraw = Column(String)
    withdrawalSharesProceeds = Column(String)


def initialize_session():
    """Initialize the database if not already initialized"""
    # create a configured "Session" class
    session_class = sessionmaker(bind=engine)

    # create a session
    session = session_class()

    # create tables
    Base.metadata.create_all(engine)

    # clear the tables
    session.query(PoolInfoTable).delete()
    session.commit()

    # commit the transaction
    session.commit()

    return session


def close_session(session):
    """Close the session"""
    session.close()


def add_pool_infos(pool_infos: list[PoolInfo], session):
    """Add a pool info to the poolinfo table"""

    for pool_info in pool_infos:
        pool_info_entry = PoolInfoTable(
            # primary key
            blockNumber=str(pool_info.blockNumber),
            # indexe),
            timeStamp=str(pool_info.timestamp),
            # othe),
            shareReserves=str(pool_info.shareReserves),
            bondReserves=str(pool_info.bondReserves),
            lpTotalSupply=str(pool_info.lpTotalSupply),
            sharePrice=str(pool_info.sharePrice),
            longsOutstanding=str(pool_info.longsOutstanding),
            longAverageMaturityTime=str(pool_info.longAverageMaturityTime),
            shortsOutstanding=str(pool_info.shortsOutstanding),
            shortAverageMaturityTime=str(pool_info.shortAverageMaturityTime),
            shortBaseVolume=str(pool_info.shortBaseVolume),
            withdrawalSharesReadyToWithdraw=str(pool_info.withdrawalSharesReadyToWithdraw),
            withdrawalSharesProceeds=str(pool_info.withdrawalSharesProceeds),
        )
        session.add(pool_info_entry)

    try:
        session.commit()
    except sqlalchemy.exc.DataError as err:  # type: ignore
        print(f"{pool_infos=}")
        raise err
