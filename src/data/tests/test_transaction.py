"""CRUD tests for Transaction"""
import numpy as np
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data import postgres
from src.data.db_schema import Base, Transaction

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
        transaction = Transaction(blockNumber=1, transactionHash="a", event_value=3.2)  # add your other columns here...
        session.add(transaction)
        session.commit()

        retrieved_transaction = session.query(Transaction).filter_by(blockNumber=1).first()
        assert retrieved_transaction is not None
        # event_value retreieved from postgres is in Decimal, cast to float
        assert float(retrieved_transaction.event_value) == 3.2

    def test_update_transaction(self, session):
        """Update an entry"""
        transaction = Transaction(blockNumber=1, transactionHash="a", event_value=3.2)
        session.add(transaction)
        session.commit()

        transaction.event_value = 5.0
        session.commit()

        updated_transaction = session.query(Transaction).filter_by(blockNumber=1).first()
        # event_value retreieved from postgres is in Decimal, cast to float
        assert float(updated_transaction.event_value) == 5.0

    def test_delete_transaction(self, session):
        """Delete an entry"""
        transaction = Transaction(blockNumber=1, transactionHash="a", event_value=3.2)
        session.add(transaction)
        session.commit()

        session.delete(transaction)
        session.commit()

        deleted_transaction = session.query(Transaction).filter_by(blockNumber=1).first()
        assert deleted_transaction is None


class TestTransactionInterface:
    """Testing postgres interface for transaction table"""

    def test_latest_block_number(self, session):
        """Testing retrevial of transaction via interface"""
        transaction_1 = Transaction(
            blockNumber=1, transactionHash="a", event_value=3.0
        )  # add your other columns here...
        postgres.add_transactions([transaction_1], session)

        latest_block_number = postgres.get_latest_block_number_from_table(Transaction, session)
        assert latest_block_number == 1

        transaction_2 = Transaction(
            blockNumber=2, transactionHash="b", event_value=3.2
        )  # add your other columns here...
        transaction_3 = Transaction(
            blockNumber=3, transactionHash="c", event_value=3.4
        )  # add your other columns here...
        postgres.add_transactions([transaction_2, transaction_3], session)

        latest_block_number = postgres.get_latest_block_number_from_table(Transaction, session)
        assert latest_block_number == 3

    def test_get_transactions(self, session):
        """Testing retrevial of transactions via interface"""
        transaction_1 = Transaction(
            blockNumber=0, transactionHash="a", event_value=3.1
        )  # add your other columns here...
        transaction_2 = Transaction(
            blockNumber=1, transactionHash="b", event_value=3.2
        )  # add your other columns here...
        transaction_3 = Transaction(
            blockNumber=2, transactionHash="c", event_value=3.3
        )  # add your other columns here...
        postgres.add_transactions([transaction_1, transaction_2, transaction_3], session)

        transactions_df = postgres.get_transactions(session)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.1, 3.2, 3.3])

    def test_block_query_transactions(self, session):
        """Testing querying by block number of transactions via interface"""
        transaction_1 = Transaction(
            blockNumber=0, transactionHash="a", event_value=3.1
        )  # add your other columns here...
        transaction_2 = Transaction(
            blockNumber=1, transactionHash="b", event_value=3.2
        )  # add your other columns here...
        transaction_3 = Transaction(
            blockNumber=2, transactionHash="c", event_value=3.3
        )  # add your other columns here...
        postgres.add_transactions([transaction_1, transaction_2, transaction_3], session)

        transactions_df = postgres.get_transactions(session, start_block=1)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.2, 3.3])

        transactions_df = postgres.get_transactions(session, start_block=-1)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.3])

        transactions_df = postgres.get_transactions(session, end_block=1)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.1])

        transactions_df = postgres.get_transactions(session, end_block=-1)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.1, 3.2])

        transactions_df = postgres.get_transactions(session, start_block=1, end_block=-1)
        np.testing.assert_array_equal(transactions_df["event_value"], [3.2])
