"""CRUD tests for PoolConfig"""
import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from eth_bots.data import postgres
from eth_bots.data.db_schema import Base, PoolConfig

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


class TestPoolConfigTable:
    """CRUD tests for poolconfig table"""

    def test_create_pool_config(self, session):
        """Create and entry"""
        pool_config = PoolConfig(contractAddress="0", initialSharePrice=3.2)  # add your other columns here...
        session.add(pool_config)
        session.commit()

        retrieved_pool_config = session.query(PoolConfig).filter_by(contractAddress="0").first()
        assert retrieved_pool_config is not None
        assert float(retrieved_pool_config.initialSharePrice) == 3.2

    def test_delete_pool_config(self, session):
        """Delete an entry"""
        pool_config = PoolConfig(contractAddress="0", initialSharePrice=3.2)  # add your other columns here...
        session.add(pool_config)
        session.commit()

        session.delete(pool_config)
        session.commit()

        deleted_pool_config = session.query(PoolConfig).filter_by(contractAddress="0").first()
        assert deleted_pool_config is None


class TestPoolConfigInterface:
    """Testing postgres interface for poolconfig table"""

    def test_get_pool_config(self, session):
        """Testing retrevial of pool config via interface"""
        pool_config_1 = PoolConfig(contractAddress="0", initialSharePrice=3.2)  # add your other columns here...
        postgres.add_pool_config(pool_config_1, session)

        pool_config_df_1 = postgres.get_pool_config(session)
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initialSharePrice"] == 3.2

        pool_config_2 = PoolConfig(contractAddress="1", initialSharePrice=3.4)  # add your other columns here...
        postgres.add_pool_config(pool_config_2, session)

        pool_config_df_2 = postgres.get_pool_config(session)
        assert len(pool_config_df_2) == 2
        np.testing.assert_array_equal(pool_config_df_2["initialSharePrice"], [3.2, 3.4])

    def test_primary_id_query_pool_config(self, session):
        """Testing retrevial of pool config via interface"""
        pool_config = PoolConfig(contractAddress="0", initialSharePrice=3.2)  # add your other columns here...
        postgres.add_pool_config(pool_config, session)

        pool_config_df_1 = postgres.get_pool_config(session, contract_address="0")
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initialSharePrice"] == 3.2

        pool_config_df_2 = postgres.get_pool_config(session, contract_address="1")
        assert len(pool_config_df_2) == 0

    def test_pool_config_verify(self, session):
        """Testing retrevial of pool config via interface"""
        pool_config_1 = PoolConfig(contractAddress="0", initialSharePrice=3.2)  # add your other columns here...
        postgres.add_pool_config(pool_config_1, session)
        pool_config_df_1 = postgres.get_pool_config(session)
        assert len(pool_config_df_1) == 1
        assert pool_config_df_1.loc[0, "initialSharePrice"] == 3.2

        # Nothing should happen if we give the same pool_config
        pool_config_2 = PoolConfig(contractAddress="0", initialSharePrice=3.2)  # add your other columns here...
        postgres.add_pool_config(pool_config_2, session)
        pool_config_df_2 = postgres.get_pool_config(session)
        assert len(pool_config_df_2) == 1
        assert pool_config_df_2.loc[0, "initialSharePrice"] == 3.2

        # If we try to add another pool config with a different value, should throw a ValueError
        pool_config_3 = PoolConfig(contractAddress="0", initialSharePrice=3.4)  # add your other columns here...
        with pytest.raises(ValueError):
            postgres.add_pool_config(pool_config_3, session)
