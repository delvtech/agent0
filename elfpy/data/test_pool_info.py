"""CRUD tests for PoolInfoTable"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from elfpy.data.postgres import Base, PoolInfoTable

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
        pool_info = PoolInfoTable(blockNumber=1, timeStamp=1628472000)  # add your other columns here...
        session.add(pool_info)
        session.commit()

        retrieved_pool_info = session.query(PoolInfoTable).filter_by(blockNumber=1).first()
        assert retrieved_pool_info is not None
        assert retrieved_pool_info.timeStamp == 1628472000

    def test_update_pool_info(self, session):
        """Update an entry"""
        pool_info = PoolInfoTable(blockNumber=1, timeStamp=1628472000)
        session.add(pool_info)
        session.commit()

        # TODO: Solve this type issue.  I read the sqlmypy can do this but I wasn't successful.
        pool_info.timeStamp = 1628472001  # type: ignore
        session.commit()

        updated_pool_info = session.query(PoolInfoTable).filter_by(blockNumber=1).first()
        assert updated_pool_info.timeStamp == 1628472001

    def test_delete_pool_info(self, session):
        """Delete an entry"""
        pool_info = PoolInfoTable(blockNumber=1, timeStamp=1628472000)
        session.add(pool_info)
        session.commit()

        session.delete(pool_info)
        session.commit()

        deleted_pool_info = session.query(PoolInfoTable).filter_by(blockNumber=1).first()
        assert deleted_pool_info is None
