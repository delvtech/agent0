"""CRUD tests for UserMap"""
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .db_schema import Base, UserMap

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


class TestUserMapTable:
    """CRUD tests for UserMap table"""

    def test_create_user_map(self, session):
        """Create and entry"""
        # Note: this test is using inmemory sqlite, which doesn't seem to support
        # autoincrementing ids without init, whereas postgres does this with no issues
        # Hence, we explicitly add id here
        user_map = UserMap(address="1", username="a")
        session.add(user_map)
        session.commit()

        retrieved_user_map = session.query(UserMap).filter_by(address="1").first()
        assert retrieved_user_map is not None
        assert retrieved_user_map.username == "a"

    def test_update_user_map(self, session):
        """Update an entry"""
        user_map = UserMap(address="1", username="a")
        session.add(user_map)
        session.commit()

        user_map.username = "b"
        session.commit()

        updated_user_map = session.query(UserMap).filter_by(address="1").first()
        # tokenValue retreieved from postgres is in Decimal, cast to float
        assert updated_user_map.username == "b"

    def test_delete_user_map(self, session):
        """Delete an entry"""
        user_map = UserMap(address="1", username="a")
        session.add(user_map)
        session.commit()

        session.delete(user_map)
        session.commit()

        deleted_user_map = session.query(UserMap).filter_by(address="1").first()
        assert deleted_user_map is None
