"""CRUD tests for UserMap"""
import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from elfpy.data import postgres
from elfpy.data.db_schema import Base, UserMap

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


class TestUserMapInterface:
    """Testing postgres interface for usermap table"""

    def test_get_user_map(self, session):
        """Testing retrevial of usermap via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        postgres.add_user_map(username=username_1, addresses=addresses_1, session=session)
        username_2 = "b"
        addresses_2 = ["4", "5"]
        postgres.add_user_map(username=username_2, addresses=addresses_2, session=session)

        # This is in order of insertion
        user_map_df = postgres.get_user_map(session)
        assert len(user_map_df) == 5
        assert user_map_df["username"].equals(pd.Series(["a", "a", "a", "b", "b"], name="username"))
        assert user_map_df["address"].equals(pd.Series(["1", "2", "3", "4", "5"], name="address"))

    def test_get_query_user_map(self, session):
        """Testing querying by block number of user map via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        postgres.add_user_map(username=username_1, addresses=addresses_1, session=session)
        username_2 = "b"
        addresses_2 = ["4", "5"]
        postgres.add_user_map(username=username_2, addresses=addresses_2, session=session)

        user_map_df = postgres.get_user_map(session, address="1")
        assert user_map_df["username"].equals(pd.Series(["a"], name="username"))
        user_map_df = postgres.get_user_map(session, address="2")
        assert user_map_df["username"].equals(pd.Series(["a"], name="username"))
        user_map_df = postgres.get_user_map(session, address="3")
        assert user_map_df["username"].equals(pd.Series(["a"], name="username"))
        user_map_df = postgres.get_user_map(session, address="4")
        assert user_map_df["username"].equals(pd.Series(["b"], name="username"))
        user_map_df = postgres.get_user_map(session, address="5")
        assert user_map_df["username"].equals(pd.Series(["b"], name="username"))

    def test_user_map_insertion_error(self, session):
        """Testing retrevial of usermap via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        postgres.add_user_map(username=username_1, addresses=addresses_1, session=session)

        # Adding the same addresses with the same username should pass
        username_2 = "a"
        addresses_2 = ["1", "2", "5"]
        postgres.add_user_map(username=username_2, addresses=addresses_2, session=session)

        user_map_df = postgres.get_user_map(session)
        assert len(user_map_df) == 4
        assert user_map_df["username"].equals(pd.Series(["a", "a", "a", "a"], name="username"))
        assert user_map_df["address"].equals(pd.Series(["1", "2", "3", "5"], name="address"))

        # Adding the same addresses with different username should fail
        username_3 = "b"
        addresses_3 = ["6", "1", "2", "4"]
        with pytest.raises(ValueError):
            postgres.add_user_map(username=username_3, addresses=addresses_3, session=session)

        # Final db values shouldn't change
        user_map_df = postgres.get_user_map(session)
        user_map_df = postgres.get_user_map(session)
        assert len(user_map_df) == 4
        assert user_map_df["username"].equals(pd.Series(["a", "a", "a", "a"], name="username"))
        assert user_map_df["address"].equals(pd.Series(["1", "2", "3", "5"], name="address"))
