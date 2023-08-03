"""CRUD tests for PoolInfo"""
from datetime import datetime

import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import src.data.hyperdrive.postgres
from src.data import postgres
from src.data.db_schema import Base
from src.data.hyperdrive.db_schema import PoolInfo

engine = create_engine("sqlite:///:memory:")  # in-memory SQLite database for testing
Session = sessionmaker(bind=engine)

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name


@pytest.fixture(scope="function")
def session():
    """Session fixture for tests"""
    Base.metadata.create_all(engine)  # create tables
    session_ = Session()
    yield session_
    session_.close()
    Base.metadata.drop_all(engine)  # drop tables


class TestPoolInfoTable:
    """CRUD tests for poolinfo table"""

    def test_create_pool_info(self, session):
        """Create and entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(blockNumber=1, timestamp=timestamp)
        session.add(pool_info)
        session.commit()

        retrieved_pool_info = session.query(PoolInfo).filter_by(blockNumber=1).first()
        assert retrieved_pool_info is not None
        assert retrieved_pool_info.timestamp == timestamp

    def test_update_pool_info(self, session):
        """Update an entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(blockNumber=1, timestamp=timestamp)
        session.add(pool_info)
        session.commit()

        # TODO: Solve this type issue.  I read the sqlmypy can do this but I wasn't successful.
        new_timestamp = datetime.fromtimestamp(1628472001)
        pool_info.timestamp = new_timestamp  # type: ignore
        session.commit()

        updated_pool_info = session.query(PoolInfo).filter_by(blockNumber=1).first()
        assert updated_pool_info.timestamp == new_timestamp

    def test_delete_pool_info(self, session):
        """Delete an entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(blockNumber=1, timestamp=timestamp)
        session.add(pool_info)
        session.commit()

        session.delete(pool_info)
        session.commit()

        deleted_pool_info = session.query(PoolInfo).filter_by(blockNumber=1).first()
        assert deleted_pool_info is None


class TestPoolInfoInterface:
    """Testing postgres interface for poolinfo table"""

    def test_latest_block_number(self, session):
        """Testing latest block number call"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(blockNumber=1, timestamp=timestamp_1)
        src.data.hyperdrive.postgres.add_pool_infos([pool_info_1], session)

        latest_block_number = postgres.get_latest_block_number(session)
        assert latest_block_number == 1

        timestamp_1 = datetime.fromtimestamp(1628472002)
        pool_info_1 = PoolInfo(blockNumber=2, timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472004)
        pool_info_2 = PoolInfo(blockNumber=3, timestamp=timestamp_2)
        src.data.hyperdrive.postgres.add_pool_infos([pool_info_1, pool_info_2], session)

        latest_block_number = postgres.get_latest_block_number(session)
        assert latest_block_number == 3

    def test_get_pool_info(self, session):
        """Testing retrevial of pool info via interface"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(blockNumber=0, timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472002)
        pool_info_2 = PoolInfo(blockNumber=1, timestamp=timestamp_2)
        timestamp_3 = datetime.fromtimestamp(1628472004)
        pool_info_3 = PoolInfo(blockNumber=2, timestamp=timestamp_3)
        src.data.hyperdrive.postgres.add_pool_infos([pool_info_1, pool_info_2, pool_info_3], session)

        pool_info_df = src.data.hyperdrive.postgres.get_pool_info(session)
        np.testing.assert_array_equal(
            pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_1, timestamp_2, timestamp_3])
        )

    def test_block_query_pool_info(self, session):
        """Testing retrevial of pool info via interface"""
        timestamp_1 = datetime.fromtimestamp(1628472000)
        pool_info_1 = PoolInfo(blockNumber=0, timestamp=timestamp_1)
        timestamp_2 = datetime.fromtimestamp(1628472002)
        pool_info_2 = PoolInfo(blockNumber=1, timestamp=timestamp_2)
        timestamp_3 = datetime.fromtimestamp(1628472004)
        pool_info_3 = PoolInfo(blockNumber=2, timestamp=timestamp_3)
        src.data.hyperdrive.postgres.add_pool_infos([pool_info_1, pool_info_2, pool_info_3], session)

        pool_info_df = src.data.hyperdrive.postgres.get_pool_info(session, start_block=1)
        np.testing.assert_array_equal(
            pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_2, timestamp_3])
        )

        pool_info_df = src.data.hyperdrive.postgres.get_pool_info(session, start_block=-1)
        np.testing.assert_array_equal(pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_3]))

        pool_info_df = src.data.hyperdrive.postgres.get_pool_info(session, end_block=1)
        np.testing.assert_array_equal(pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_1]))

        pool_info_df = src.data.hyperdrive.postgres.get_pool_info(session, end_block=-1)
        np.testing.assert_array_equal(
            pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_1, timestamp_2])
        )

        pool_info_df = src.data.hyperdrive.postgres.get_pool_info(session, start_block=1, end_block=-1)
        np.testing.assert_array_equal(pool_info_df["timestamp"].dt.to_pydatetime(), np.array([timestamp_2]))
