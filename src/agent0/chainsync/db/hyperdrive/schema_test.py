"""CRUD tests for Transaction"""

from datetime import datetime
from decimal import Decimal

import pytest
from sqlalchemy.orm import Session

from .schema import CheckpointInfo, PoolConfig, PoolInfo

# These tests are using fixtures defined in conftest.py


class TestCheckpointTable:
    """CRUD tests for checkpoint table"""

    @pytest.mark.docker
    def test_create_checkpoint(self, db_session: Session):
        """Create and entry"""
        vault_share_price = Decimal("1.1")
        checkpoint = CheckpointInfo(checkpoint_time=1, hyperdrive_address="a", vault_share_price=vault_share_price)
        db_session.add(checkpoint)
        db_session.commit()

        retrieved_checkpoint = db_session.query(CheckpointInfo).filter_by(checkpoint_time=1).first()
        assert retrieved_checkpoint is not None
        assert retrieved_checkpoint.vault_share_price == vault_share_price

    @pytest.mark.docker
    def test_update_checkpoint(self, db_session: Session):
        """Update an entry"""
        vault_share_price = Decimal("1.1")
        checkpoint = CheckpointInfo(checkpoint_time=1, hyperdrive_address="a", vault_share_price=vault_share_price)
        db_session.add(checkpoint)
        db_session.commit()

        checkpoint.vault_share_price = Decimal("5.0")
        db_session.commit()

        updated_checkpoint = db_session.query(CheckpointInfo).filter_by(checkpoint_time=1).first()
        assert updated_checkpoint is not None
        assert updated_checkpoint.vault_share_price == Decimal("5.0")

    @pytest.mark.docker
    def test_delete_checkpoint(self, db_session: Session):
        """Delete an entry"""
        vault_share_price = Decimal("1.1")
        checkpoint = CheckpointInfo(checkpoint_time=1, hyperdrive_address="a", vault_share_price=vault_share_price)
        db_session.add(checkpoint)
        db_session.commit()

        db_session.delete(checkpoint)
        db_session.commit()

        deleted_checkpoint = db_session.query(CheckpointInfo).filter_by(checkpoint_time=1).first()
        assert deleted_checkpoint is None


class TestPoolConfigTable:
    """CRUD tests for poolconfig table"""

    @pytest.mark.docker
    def test_create_pool_config(self, db_session: Session):
        """Create and entry"""
        pool_config = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.2"))
        db_session.add(pool_config)
        db_session.commit()

        retrieved_pool_config = db_session.query(PoolConfig).filter_by(hyperdrive_address="0").first()
        assert retrieved_pool_config is not None
        assert retrieved_pool_config.initial_vault_share_price is not None
        assert float(retrieved_pool_config.initial_vault_share_price) == 3.2

    @pytest.mark.docker
    def test_delete_pool_config(self, db_session: Session):
        """Delete an entry"""
        pool_config = PoolConfig(hyperdrive_address="0", initial_vault_share_price=Decimal("3.2"))
        db_session.add(pool_config)
        db_session.commit()

        db_session.delete(pool_config)
        db_session.commit()

        deleted_pool_config = db_session.query(PoolConfig).filter_by(hyperdrive_address="0").first()
        assert deleted_pool_config is None


class TestPoolInfoTable:
    """CRUD tests for poolinfo table"""

    @pytest.mark.docker
    def test_create_pool_info(self, db_session: Session):
        """Create and entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(block_number=1, hyperdrive_address="a", timestamp=timestamp)
        db_session.add(pool_info)
        db_session.commit()

        retrieved_pool_info = db_session.query(PoolInfo).filter_by(block_number=1).first()
        assert retrieved_pool_info is not None
        assert retrieved_pool_info.timestamp == timestamp

    @pytest.mark.docker
    def test_update_pool_info(self, db_session: Session):
        """Update an entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(block_number=1, hyperdrive_address="a", timestamp=timestamp)
        db_session.add(pool_info)
        db_session.commit()

        # TODO: Solve this type issue.  I read the sqlmypy can do this but I wasn't successful.
        new_timestamp = datetime.fromtimestamp(1628472001)
        pool_info.timestamp = new_timestamp  # type: ignore
        db_session.commit()

        updated_pool_info = db_session.query(PoolInfo).filter_by(block_number=1).first()
        assert updated_pool_info is not None
        assert updated_pool_info.timestamp == new_timestamp

    @pytest.mark.docker
    def test_delete_pool_info(self, db_session: Session):
        """Delete an entry"""
        timestamp = datetime.fromtimestamp(1628472000)
        pool_info = PoolInfo(block_number=1, hyperdrive_address="a", timestamp=timestamp)
        db_session.add(pool_info)
        db_session.commit()

        db_session.delete(pool_info)
        db_session.commit()

        deleted_pool_info = db_session.query(PoolInfo).filter_by(block_number=1).first()
        assert deleted_pool_info is None
