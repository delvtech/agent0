"""CRUD tests for Transaction"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from elfpy.data.postgres import Base, Transaction

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

    def test_create_transaction(self, session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        transaction = Transaction(blockNumber=1, event_value=3.2)  # add your other columns here...
        session.add(transaction)
        session.commit()

        retrieved_transaction = session.query(Transaction).filter_by(blockNumber=1).first()
        assert retrieved_transaction is not None
        # event_value retreieved from postgres is in Decimal, cast to float
        assert float(retrieved_transaction.event_value) == 3.2

    def test_update_pool_info(self, session):
        """Update an entry"""
        transaction = Transaction(blockNumber=1, event_value=3.2)
        session.add(transaction)
        session.commit()

        transaction.event_value = 5.0
        session.commit()

        updated_pool_info = session.query(Transaction).filter_by(blockNumber=1).first()
        # event_value retreieved from postgres is in Decimal, cast to float
        assert float(updated_pool_info.event_value) == 5.0

    def test_delete_pool_info(self, session):
        """Delete an entry"""
        transaction = Transaction(blockNumber=1, event_value=3.2)
        session.add(transaction)
        session.commit()

        session.delete(transaction)
        session.commit()

        deleted_transaction = session.query(Transaction).filter_by(blockNumber=1).first()
        assert deleted_transaction is None
