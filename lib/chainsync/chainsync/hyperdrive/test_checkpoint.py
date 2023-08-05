"""CRUD tests for CheckpointInfo"""
from datetime import datetime
from decimal import Decimal

import numpy as np
import pytest
from chainsync.base import Base, get_latest_block_number_from_table
from chainsync.hyperdrive import CheckpointInfo, add_checkpoint_infos, get_checkpoint_info
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///:memory:")  # in-memory SQLite database for testing
Session = sessionmaker(bind=engine)

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name
# pylint: disable=invalid-name


@pytest.fixture(scope="function")
def session():
    """Session fixture for tests"""
    Base.metadata.create_all(engine)  # create tables
    session_ = Session()
    yield session_
    session_.close()
    Base.metadata.drop_all(engine)  # drop tables


class TestCheckpointTable:
    """CRUD tests for checkpoint table"""

    def test_create_checkpoint(self, session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        timestamp = datetime.now()
        checkpoint = CheckpointInfo(blockNumber=1, timestamp=timestamp)
        add_checkpoint_infos([checkpoint], session)
        session.commit()

        retrieved_checkpoint = session.query(CheckpointInfo).filter_by(blockNumber=1).first()
        assert retrieved_checkpoint is not None
        assert retrieved_checkpoint.timestamp == timestamp

    def test_update_checkpoint(self, session):
        """Update an entry"""
        timestamp = datetime.now()
        checkpoint = CheckpointInfo(blockNumber=1, timestamp=timestamp)
        add_checkpoint_infos([checkpoint], session)
        session.commit()

        checkpoint.sharePrice = Decimal("5.0")
        session.commit()

        updated_checkpoint = session.query(CheckpointInfo).filter_by(blockNumber=1).first()
        assert updated_checkpoint.sharePrice == 5.0

    def test_delete_checkpoint(self, session):
        """Delete an entry"""
        timestamp = datetime.now()
        checkpoint = CheckpointInfo(blockNumber=1, timestamp=timestamp)
        add_checkpoint_infos([checkpoint], session)
        session.commit()

        session.delete(checkpoint)
        session.commit()

        deleted_checkpoint = session.query(CheckpointInfo).filter_by(blockNumber=1).first()
        assert deleted_checkpoint is None


class TestCheckpointInterface:
    """Testing postgres interface for checkpoint table"""

    def test_latest_block_number(self, session):
        """Testing retrevial of checkpoint via interface"""
        checkpoint_1 = CheckpointInfo(blockNumber=1, timestamp=datetime.now())
        add_checkpoint_infos([checkpoint_1], session)
        session.commit()

        latest_block_number = get_latest_block_number_from_table(CheckpointInfo, session)
        assert latest_block_number == 1

        checkpoint_2 = CheckpointInfo(blockNumber=2, timestamp=datetime.now())
        checkpoint_3 = CheckpointInfo(blockNumber=3, timestamp=datetime.now())
        add_checkpoint_infos([checkpoint_2, checkpoint_3], session)

        latest_block_number = get_latest_block_number_from_table(CheckpointInfo, session)
        assert latest_block_number == 3

    def test_get_checkpoints(self, session):
        """Testing retrevial of checkpoints via interface"""
        date_1 = datetime(1945, 8, 6)
        date_2 = datetime(1984, 8, 9)
        date_3 = datetime(2001, 9, 11)
        checkpoint_1 = CheckpointInfo(blockNumber=0, timestamp=date_1)
        checkpoint_2 = CheckpointInfo(blockNumber=1, timestamp=date_2)
        checkpoint_3 = CheckpointInfo(blockNumber=2, timestamp=date_3)
        add_checkpoint_infos([checkpoint_1, checkpoint_2, checkpoint_3], session)

        checkpoints_df = get_checkpoint_info(session)
        np.testing.assert_array_equal(
            checkpoints_df["timestamp"].dt.to_pydatetime(), np.array([date_1, date_2, date_3])
        )

    def test_block_query_checkpoints(self, session):
        """Testing querying by block number of checkpoints via interface"""
        checkpoint_1 = CheckpointInfo(blockNumber=0, timestamp=datetime.now(), sharePrice=Decimal("3.1"))
        checkpoint_2 = CheckpointInfo(blockNumber=1, timestamp=datetime.now(), sharePrice=Decimal("3.2"))
        checkpoint_3 = CheckpointInfo(blockNumber=2, timestamp=datetime.now(), sharePrice=Decimal("3.3"))
        add_checkpoint_infos([checkpoint_1, checkpoint_2, checkpoint_3], session)

        checkpoints_df = get_checkpoint_info(session, start_block=1)
        np.testing.assert_array_equal(checkpoints_df["sharePrice"], [3.2, 3.3])

        checkpoints_df = get_checkpoint_info(session, start_block=-1)
        np.testing.assert_array_equal(checkpoints_df["sharePrice"], [3.3])

        checkpoints_df = get_checkpoint_info(session, end_block=1)
        np.testing.assert_array_equal(checkpoints_df["sharePrice"], [3.1])

        checkpoints_df = get_checkpoint_info(session, end_block=-1)
        np.testing.assert_array_equal(checkpoints_df["sharePrice"], [3.1, 3.2])

        checkpoints_df = get_checkpoint_info(session, start_block=1, end_block=-1)
        np.testing.assert_array_equal(checkpoints_df["sharePrice"], [3.2])
