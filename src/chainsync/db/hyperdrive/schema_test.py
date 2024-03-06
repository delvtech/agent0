"""CRUD tests for Transaction"""

from datetime import datetime
from decimal import Decimal

import pytest

from .schema import CheckpointInfo, HyperdriveTransaction, PoolConfig, PoolInfo, WalletDelta

# These tests are using fixtures defined in conftest.py


class TestTransactionTable:
    """CRUD tests for transaction table"""

    @pytest.mark.docker
    def test_create_transaction(self, db_session):
        """Create and entry"""
        transaction = HyperdriveTransaction(block_number=1, transaction_hash="a", event_value=Decimal("3.2"))
        db_session.add(transaction)
        db_session.commit()

        retrieved_transaction = db_session.query(HyperdriveTransaction).filter_by(block_number=1).first()
        assert retrieved_transaction is not None
        # event_value retrieved from postgres is in Decimal, cast to float
        assert float(retrieved_transaction.event_value) == 3.2

    @pytest.mark.docker
    def test_update_transaction(self, db_session):
        """Update an entry"""
        transaction = HyperdriveTransaction(block_number=1, transaction_hash="a", event_value=Decimal("3.2"))
        db_session.add(transaction)
        db_session.commit()

        transaction.event_value = Decimal("5.0")
        db_session.commit()

        updated_transaction = db_session.query(HyperdriveTransaction).filter_by(block_number=1).first()
        # event_value retrieved from postgres is in Decimal, cast to float
        assert float(updated_transaction.event_value) == 5.0

    @pytest.mark.docker
    def test_delete_transaction(self, db_session):
        """Delete an entry"""
        transaction = HyperdriveTransaction(block_number=1, transaction_hash="a", event_value=Decimal("3.2"))
        db_session.add(transaction)
        db_session.commit()

        db_session.delete(transaction)
        db_session.commit()

        deleted_transaction = db_session.query(HyperdriveTransaction).filter_by(block_number=1).first()
        assert deleted_transaction is None


class TestCheckpointTable:
    """CRUD tests for checkpoint table"""

    @pytest.mark.docker
    def test_create_checkpoint(self, db_session):
        """Create and entry"""
        vault_share_price = Decimal("1.1")
        checkpoint = CheckpointInfo(checkpoint_time=1, vault_share_price=vault_share_price)
        db_session.add(checkpoint)
        db_session.commit()

        retrieved_checkpoint = db_session.query(CheckpointInfo).filter_by(checkpoint_time=1).first()
        assert retrieved_checkpoint is not None
        assert retrieved_checkpoint.vault_share_price == vault_share_price

    @pytest.mark.docker
    def test_update_checkpoint(self, db_session):
        """Update an entry"""
        vault_share_price = Decimal("1.1")
        checkpoint = CheckpointInfo(checkpoint_time=1, vault_share_price=vault_share_price)
        db_session.add(checkpoint)
        db_session.commit()

        checkpoint.vault_share_price = Decimal("5.0")
        db_session.commit()

        updated_checkpoint = db_session.query(CheckpointInfo).filter_by(checkpoint_time=1).first()
        assert updated_checkpoint.vault_share_price == Decimal("5.0")

    @pytest.mark.docker
    def test_delete_checkpoint(self, db_session):
        """Delete an entry"""
        vault_share_price = Decimal("1.1")
        checkpoint = CheckpointInfo(checkpoint_time=1, vault_share_price=vault_share_price)
        db_session.add(checkpoint)
        db_session.commit()

        db_session.delete(checkpoint)
        db_session.commit()

        deleted_checkpoint = db_session.query(CheckpointInfo).filter_by(checkpoint_time=1).first()
        assert deleted_checkpoint is None


class TestPoolConfigTable:
    """CRUD tests for poolconfig table"""

    @pytest.mark.docker
    def test_create_pool_config(self, db_session):
        """Create and entry"""
        pool_config = PoolConfig(contract_address="0", initial_vault_share_price=Decimal("3.2"))
        db_session.add(pool_config)
        db_session.commit()

        retrieved_pool_config = db_session.query(PoolConfig).filter_by(contract_address="0").first()
        assert retrieved_pool_config is not None
        assert float(retrieved_pool_config.initial_vault_share_price) == 3.2

    @pytest.mark.docker
    def test_delete_pool_config(self, db_session):
        """Delete an entry"""
        pool_config = PoolConfig(contract_address="0", initial_vault_share_price=Decimal("3.2"))
        db_session.add(pool_config)
        db_session.commit()

        db_session.delete(pool_config)
        db_session.commit()

        deleted_pool_config = db_session.query(PoolConfig).filter_by(contract_address="0").first()
        assert deleted_pool_config is None


class TestPoolInfoTable:
    """CRUD tests for poolinfo table"""

    @pytest.mark.docker
    def test_create_pool_info(self, db_session):
        """Create and entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(block_number=1, timestamp=timestamp)
        db_session.add(pool_info)
        db_session.commit()

        retrieved_pool_info = db_session.query(PoolInfo).filter_by(block_number=1).first()
        assert retrieved_pool_info is not None
        assert retrieved_pool_info.timestamp == timestamp

    @pytest.mark.docker
    def test_update_pool_info(self, db_session):
        """Update an entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(block_number=1, timestamp=timestamp)
        db_session.add(pool_info)
        db_session.commit()

        # TODO: Solve this type issue.  I read the sqlmypy can do this but I wasn't successful.
        new_timestamp = datetime.fromtimestamp(1628472001)
        pool_info.timestamp = new_timestamp  # type: ignore
        db_session.commit()

        updated_pool_info = db_session.query(PoolInfo).filter_by(block_number=1).first()
        assert updated_pool_info.timestamp == new_timestamp

    @pytest.mark.docker
    def test_delete_pool_info(self, db_session):
        """Delete an entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(block_number=1, timestamp=timestamp)
        db_session.add(pool_info)
        db_session.commit()

        db_session.delete(pool_info)
        db_session.commit()

        deleted_pool_info = db_session.query(PoolInfo).filter_by(block_number=1).first()
        assert deleted_pool_info is None


class TestWalletDeltaTable:
    """CRUD tests for WalletDelta table"""

    @pytest.mark.docker
    def test_create_wallet_delta(self, db_session):
        """Create and entry"""
        wallet_delta = WalletDelta(block_number=1, transaction_hash="a", delta=Decimal("3.2"))
        db_session.add(wallet_delta)
        db_session.commit()

        retrieved_wallet_delta = db_session.query(WalletDelta).filter_by(block_number=1).first()
        assert retrieved_wallet_delta is not None
        # tokenValue retrieved from postgres is in Decimal, cast to float
        assert float(retrieved_wallet_delta.delta) == 3.2

    @pytest.mark.docker
    def test_update_wallet_delta(self, db_session):
        """Update an entry"""
        wallet_delta = WalletDelta(block_number=1, transaction_hash="a", delta=Decimal("3.2"))
        db_session.add(wallet_delta)
        db_session.commit()
        wallet_delta.delta = Decimal("5.0")
        db_session.commit()
        updated_wallet_delta = db_session.query(WalletDelta).filter_by(block_number=1).first()
        # delta retrieved from postgres is in Decimal, cast to float
        assert float(updated_wallet_delta.delta) == 5.0

    @pytest.mark.docker
    def test_delete_wallet_delta(self, db_session):
        """Delete an entry"""
        wallet_delta = WalletDelta(block_number=1, transaction_hash="a", delta=Decimal("3.2"))
        db_session.add(wallet_delta)
        db_session.commit()
        db_session.delete(wallet_delta)
        db_session.commit()
        deleted_wallet_delta = db_session.query(WalletDelta).filter_by(block_number=1).first()
        assert deleted_wallet_delta is None
