"""CRUD tests for Transaction"""
from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from ..base.db_schema import Base
from .db_schema import CheckpointInfo, HyperdriveTransaction, PoolConfig, PoolInfo, WalletDelta, WalletInfo

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


class TestTransactionTable:
    """CRUD tests for transaction table"""

    def test_create_transaction(self, session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        transaction = HyperdriveTransaction(blockNumber=1, transactionHash="a", event_value=Decimal("3.2"))
        session.add(transaction)
        session.commit()

        retrieved_transaction = session.query(HyperdriveTransaction).filter_by(blockNumber=1).first()
        assert retrieved_transaction is not None
        # event_value retreieved from postgres is in Decimal, cast to float
        assert float(retrieved_transaction.event_value) == 3.2

    def test_update_transaction(self, session):
        """Update an entry"""
        transaction = HyperdriveTransaction(blockNumber=1, transactionHash="a", event_value=Decimal("3.2"))
        session.add(transaction)
        session.commit()

        transaction.event_value = Decimal("5.0")
        session.commit()

        updated_transaction = session.query(HyperdriveTransaction).filter_by(blockNumber=1).first()
        # event_value retreieved from postgres is in Decimal, cast to float
        assert float(updated_transaction.event_value) == 5.0

    def test_delete_transaction(self, session):
        """Delete an entry"""
        transaction = HyperdriveTransaction(blockNumber=1, transactionHash="a", event_value=Decimal("3.2"))
        session.add(transaction)
        session.commit()

        session.delete(transaction)
        session.commit()

        deleted_transaction = session.query(HyperdriveTransaction).filter_by(blockNumber=1).first()
        assert deleted_transaction is None


class TestCheckpointTable:
    """CRUD tests for checkpoint table"""

    def test_create_checkpoint(self, session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        timestamp = datetime.now()
        checkpoint = CheckpointInfo(blockNumber=1, timestamp=timestamp)
        session.add(checkpoint)
        session.commit()

        retrieved_checkpoint = session.query(CheckpointInfo).filter_by(blockNumber=1).first()
        assert retrieved_checkpoint is not None
        assert retrieved_checkpoint.timestamp == timestamp

    def test_update_checkpoint(self, session):
        """Update an entry"""
        timestamp = datetime.now()
        checkpoint = CheckpointInfo(blockNumber=1, timestamp=timestamp)
        session.add(checkpoint)
        session.commit()

        checkpoint.sharePrice = Decimal("5.0")
        session.commit()

        updated_checkpoint = session.query(CheckpointInfo).filter_by(blockNumber=1).first()
        assert updated_checkpoint.sharePrice == 5.0

    def test_delete_checkpoint(self, session):
        """Delete an entry"""
        timestamp = datetime.now()
        checkpoint = CheckpointInfo(blockNumber=1, timestamp=timestamp)
        session.add(checkpoint)
        session.commit()

        session.delete(checkpoint)
        session.commit()

        deleted_checkpoint = session.query(CheckpointInfo).filter_by(blockNumber=1).first()
        assert deleted_checkpoint is None


class TestPoolConfigTable:
    """CRUD tests for poolconfig table"""

    def test_create_pool_config(self, session):
        """Create and entry"""
        pool_config = PoolConfig(contractAddress="0", initialSharePrice=Decimal("3.2"))
        session.add(pool_config)
        session.commit()

        retrieved_pool_config = session.query(PoolConfig).filter_by(contractAddress="0").first()
        assert retrieved_pool_config is not None
        assert float(retrieved_pool_config.initialSharePrice) == 3.2

    def test_delete_pool_config(self, session):
        """Delete an entry"""
        pool_config = PoolConfig(contractAddress="0", initialSharePrice=Decimal("3.2"))
        session.add(pool_config)
        session.commit()

        session.delete(pool_config)
        session.commit()

        deleted_pool_config = session.query(PoolConfig).filter_by(contractAddress="0").first()
        assert deleted_pool_config is None


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


class TestWalletDeltaTable:
    """CRUD tests for WalletDelta table"""

    def test_create_wallet_delta(self, session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        wallet_delta = WalletDelta(blockNumber=1, transactionHash="a", delta=Decimal("3.2"))
        session.add(wallet_delta)
        session.commit()

        retrieved_wallet_delta = session.query(WalletDelta).filter_by(blockNumber=1).first()
        assert retrieved_wallet_delta is not None
        # toekValue retreieved from postgres is in Decimal, cast to float
        assert float(retrieved_wallet_delta.delta) == 3.2

    def test_update_wallet_delta(self, session):
        """Update an entry"""
        wallet_delta = WalletDelta(blockNumber=1, transactionHash="a", delta=Decimal("3.2"))
        session.add(wallet_delta)
        session.commit()
        wallet_delta.delta = Decimal("5.0")
        session.commit()
        updated_wallet_delta = session.query(WalletDelta).filter_by(blockNumber=1).first()
        # delta retreieved from postgres is in Decimal, cast to float
        assert float(updated_wallet_delta.delta) == 5.0

    def test_delete_wallet_delta(self, session):
        """Delete an entry"""
        wallet_delta = WalletDelta(blockNumber=1, transactionHash="a", delta=Decimal("3.2"))
        session.add(wallet_delta)
        session.commit()
        session.delete(wallet_delta)
        session.commit()
        deleted_wallet_delta = session.query(WalletDelta).filter_by(blockNumber=1).first()
        assert deleted_wallet_delta is None


class TestWalletInfoTable:
    """CRUD tests for WalletInfo table"""

    def test_create_wallet_info(self, session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        wallet_info = WalletInfo(blockNumber=1, tokenValue=Decimal("3.2"))
        session.add(wallet_info)
        session.commit()
        retrieved_wallet_info = session.query(WalletInfo).filter_by(blockNumber=1).first()
        assert retrieved_wallet_info is not None
        # toekValue retreieved from postgres is in Decimal, cast to float
        assert float(retrieved_wallet_info.tokenValue) == 3.2

    def test_update_wallet_info(self, session):
        """Update an entry"""
        wallet_info = WalletInfo(blockNumber=1, tokenValue=Decimal("3.2"))
        session.add(wallet_info)
        session.commit()
        wallet_info.tokenValue = Decimal("5.0")
        session.commit()
        updated_wallet_info = session.query(WalletInfo).filter_by(blockNumber=1).first()
        # tokenValue retreieved from postgres is in Decimal, cast to float
        assert float(updated_wallet_info.tokenValue) == 5.0

    def test_delete_wallet_info(self, session):
        """Delete an entry"""
        wallet_info = WalletInfo(blockNumber=1, tokenValue=Decimal("3.2"))
        session.add(wallet_info)
        session.commit()
        session.delete(wallet_info)
        session.commit()
        deleted_wallet_info = session.query(WalletInfo).filter_by(blockNumber=1).first()
        assert deleted_wallet_info is None
