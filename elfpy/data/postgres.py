"""Initialize Postgres Server"""

from sqlalchemy import Column, ForeignKey, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from elfpy.data.pool_info import PoolInfo

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

    __tablename__ = "poolinfo"

    blockNumber = Column(Integer, primary_key=True)
    timeStamp = Column(Integer, index=True)

    amount = Column(Integer)
    shareReserves = Column(Integer)
    bondReserves = Column(Integer)
    lpTotalSupply = Column(Integer)
    sharePrice = Column(Integer)
    longsOutstanding = Column(Integer)
    longAverageMaturityTime = Column(Integer)
    shortsOutstanding = Column(Integer)
    shortAverageMaturityTime = Column(Integer)
    shortBaseVolume = Column(Integer)
    withdrawalSharesReadyToWithdraw = Column(Integer)
    withdrawalSharesProceeds = Column(Integer)


def initialize_session():
    """Initialize the database if not already initialized"""
    # create a configured "Session" class
    session_class = sessionmaker(bind=engine)

    # create a session
    session = session_class()

    # clear the tables
    session.query(PoolInfoTable).delete()
    session.commit()

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
        pool_info_entry = PoolInfoTable(
            # primary key
            blockNumber=pool_info.blockNumber,
            # indexed
            timeStamp=pool_info.timestamp,
            # other
            shareReserves=pool_info.shareReserves,
            bondReserves=pool_info.bondReserves,
            lpTotalSupply=pool_info.lpTotalSupply,
            sharePrice=pool_info.sharePrice,
            longsOutstanding=pool_info.longsOutstanding,
            longAverageMaturityTime=pool_info.longAverageMaturityTime,
            shortsOutstanding=pool_info.shortsOutstanding,
            shortAverageMaturityTime=pool_info.shortAverageMaturityTime,
            shortBaseVolume=pool_info.shortBaseVolume,
            withdrawalSharesReadyToWithdraw=pool_info.withdrawalSharesReadyToWithdraw,
            withdrawalSharesProceeds=pool_info.withdrawalSharesProceeds,
        )
        session.add(pool_info_entry)

    session.commit()
