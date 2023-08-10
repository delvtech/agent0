"""CRUD tests for Transaction"""
from datetime import datetime
from decimal import Decimal

from chainsync.test_fixtures import db_session  # pylint: disable=unused-import

from .schema import CheckpointInfo, HyperdriveTransaction, PoolConfig, PoolInfo, WalletDelta, WalletInfo


class TestTransactionTable:
    """CRUD tests for transaction table"""

    def test_create_transaction(self, db_session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        transaction = HyperdriveTransaction(blockNumber=1, transactionHash="a", event_value=Decimal("3.2"))
        db_session.add(transaction)
        db_session.commit()

        retrieved_transaction = db_session.query(HyperdriveTransaction).filter_by(blockNumber=1).first()
        assert retrieved_transaction is not None
        # event_value retreieved from postgres is in Decimal, cast to float
        assert float(retrieved_transaction.event_value) == 3.2

    def test_update_transaction(self, db_session):
        """Update an entry"""
        transaction = HyperdriveTransaction(blockNumber=1, transactionHash="a", event_value=Decimal("3.2"))
        db_session.add(transaction)
        db_session.commit()

        transaction.event_value = Decimal("5.0")
        db_session.commit()

        updated_transaction = db_session.query(HyperdriveTransaction).filter_by(blockNumber=1).first()
        # event_value retreieved from postgres is in Decimal, cast to float
        assert float(updated_transaction.event_value) == 5.0

    def test_delete_transaction(self, db_session):
        """Delete an entry"""
        transaction = HyperdriveTransaction(blockNumber=1, transactionHash="a", event_value=Decimal("3.2"))
        db_session.add(transaction)
        db_session.commit()

        db_session.delete(transaction)
        db_session.commit()

        deleted_transaction = db_session.query(HyperdriveTransaction).filter_by(blockNumber=1).first()
        assert deleted_transaction is None


class TestCheckpointTable:
    """CRUD tests for checkpoint table"""

    def test_create_checkpoint(self, db_session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        timestamp = datetime.now()
        checkpoint = CheckpointInfo(blockNumber=1, timestamp=timestamp)
        db_session.add(checkpoint)
        db_session.commit()

        retrieved_checkpoint = db_session.query(CheckpointInfo).filter_by(blockNumber=1).first()
        assert retrieved_checkpoint is not None
        assert retrieved_checkpoint.timestamp == timestamp

    def test_update_checkpoint(self, db_session):
        """Update an entry"""
        timestamp = datetime.now()
        checkpoint = CheckpointInfo(blockNumber=1, timestamp=timestamp)
        db_session.add(checkpoint)
        db_session.commit()

        checkpoint.sharePrice = Decimal("5.0")
        db_session.commit()

        updated_checkpoint = db_session.query(CheckpointInfo).filter_by(blockNumber=1).first()
        assert updated_checkpoint.sharePrice == 5.0

    def test_delete_checkpoint(self, db_session):
        """Delete an entry"""
        timestamp = datetime.now()
        checkpoint = CheckpointInfo(blockNumber=1, timestamp=timestamp)
        db_session.add(checkpoint)
        db_session.commit()

        db_session.delete(checkpoint)
        db_session.commit()

        deleted_checkpoint = db_session.query(CheckpointInfo).filter_by(blockNumber=1).first()
        assert deleted_checkpoint is None


class TestPoolConfigTable:
    """CRUD tests for poolconfig table"""

    def test_create_pool_config(self, db_session):
        """Create and entry"""
        pool_config = PoolConfig(contractAddress="0", initialSharePrice=Decimal("3.2"))
        db_session.add(pool_config)
        db_session.commit()

        retrieved_pool_config = db_session.query(PoolConfig).filter_by(contractAddress="0").first()
        assert retrieved_pool_config is not None
        assert float(retrieved_pool_config.initialSharePrice) == 3.2

    def test_delete_pool_config(self, db_session):
        """Delete an entry"""
        pool_config = PoolConfig(contractAddress="0", initialSharePrice=Decimal("3.2"))
        db_session.add(pool_config)
        db_session.commit()

        db_session.delete(pool_config)
        db_session.commit()

        deleted_pool_config = db_session.query(PoolConfig).filter_by(contractAddress="0").first()
        assert deleted_pool_config is None


class TestPoolInfoTable:
    """CRUD tests for poolinfo table"""

    def test_create_pool_info(self, db_session):
        """Create and entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(blockNumber=1, timestamp=timestamp)
        db_session.add(pool_info)
        db_session.commit()

        retrieved_pool_info = db_session.query(PoolInfo).filter_by(blockNumber=1).first()
        assert retrieved_pool_info is not None
        assert retrieved_pool_info.timestamp == timestamp

    def test_update_pool_info(self, db_session):
        """Update an entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(blockNumber=1, timestamp=timestamp)
        db_session.add(pool_info)
        db_session.commit()

        # TODO: Solve this type issue.  I read the sqlmypy can do this but I wasn't successful.
        new_timestamp = datetime.fromtimestamp(1628472001)
        pool_info.timestamp = new_timestamp  # type: ignore
        db_session.commit()

        updated_pool_info = db_session.query(PoolInfo).filter_by(blockNumber=1).first()
        assert updated_pool_info.timestamp == new_timestamp

    def test_delete_pool_info(self, db_session):
        """Delete an entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(blockNumber=1, timestamp=timestamp)
        db_session.add(pool_info)
        db_session.commit()

        db_session.delete(pool_info)
        db_session.commit()

        deleted_pool_info = db_session.query(PoolInfo).filter_by(blockNumber=1).first()
        assert deleted_pool_info is None


class TestWalletDeltaTable:
    """CRUD tests for WalletDelta table"""

    def test_create_wallet_delta(self, db_session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        wallet_delta = WalletDelta(blockNumber=1, transactionHash="a", delta=Decimal("3.2"))
        db_session.add(wallet_delta)
        db_session.commit()

        retrieved_wallet_delta = db_session.query(WalletDelta).filter_by(blockNumber=1).first()
        assert retrieved_wallet_delta is not None
        # toekValue retreieved from postgres is in Decimal, cast to float
        assert float(retrieved_wallet_delta.delta) == 3.2

    def test_update_wallet_delta(self, db_session):
        """Update an entry"""
        wallet_delta = WalletDelta(blockNumber=1, transactionHash="a", delta=Decimal("3.2"))
        db_session.add(wallet_delta)
        db_session.commit()
        wallet_delta.delta = Decimal("5.0")
        db_session.commit()
        updated_wallet_delta = db_session.query(WalletDelta).filter_by(blockNumber=1).first()
        # delta retreieved from postgres is in Decimal, cast to float
        assert float(updated_wallet_delta.delta) == 5.0

    def test_delete_wallet_delta(self, db_session):
        """Delete an entry"""
        wallet_delta = WalletDelta(blockNumber=1, transactionHash="a", delta=Decimal("3.2"))
        db_session.add(wallet_delta)
        db_session.commit()
        db_session.delete(wallet_delta)
        db_session.commit()
        deleted_wallet_delta = db_session.query(WalletDelta).filter_by(blockNumber=1).first()
        assert deleted_wallet_delta is None


class TestWalletInfoTable:
    """CRUD tests for WalletInfo table"""

    def test_create_wallet_info(self, db_session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        wallet_info = WalletInfo(blockNumber=1, tokenValue=Decimal("3.2"))
        db_session.add(wallet_info)
        db_session.commit()
        retrieved_wallet_info = db_session.query(WalletInfo).filter_by(blockNumber=1).first()
        assert retrieved_wallet_info is not None
        # toekValue retreieved from postgres is in Decimal, cast to float
        assert float(retrieved_wallet_info.tokenValue) == 3.2

    def test_update_wallet_info(self, db_session):
        """Update an entry"""
        wallet_info = WalletInfo(blockNumber=1, tokenValue=Decimal("3.2"))
        db_session.add(wallet_info)
        db_session.commit()
        wallet_info.tokenValue = Decimal("5.0")
        db_session.commit()
        updated_wallet_info = db_session.query(WalletInfo).filter_by(blockNumber=1).first()
        # tokenValue retreieved from postgres is in Decimal, cast to float
        assert float(updated_wallet_info.tokenValue) == 5.0

    def test_delete_wallet_info(self, db_session):
        """Delete an entry"""
        wallet_info = WalletInfo(blockNumber=1, tokenValue=Decimal("3.2"))
        db_session.add(wallet_info)
        db_session.commit()
        db_session.delete(wallet_info)
        db_session.commit()
        deleted_wallet_info = db_session.query(WalletInfo).filter_by(blockNumber=1).first()
        assert deleted_wallet_info is None
