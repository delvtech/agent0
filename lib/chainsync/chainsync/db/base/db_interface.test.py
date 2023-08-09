"""CRUD tests for CheckpointInfo"""
import numpy as np
import pytest
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, sessionmaker

from .db_interface import add_user_map, drop_table, get_user_map, query_tables

engine = create_engine("sqlite:///:memory:")  # in-memory SQLite database for testing
Session = sessionmaker(bind=engine)

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name, too-few-public-methods


class Based(MappedAsDataclass, DeclarativeBase):
    """Base class to subclass from to define the schema"""


class Very(Based):
    """Dummy but very sincere table schema."""

    __tablename__ = "verybased"

    key: Mapped[str] = mapped_column(String, primary_key=True)


class DropMe(Based):
    """Dummy table schema that wants to be dropped."""

    __tablename__ = "dropme"

    key: Mapped[str] = mapped_column(String, primary_key=True)


@pytest.fixture(scope="function")
def session():
    """Session fixture for tests"""
    Based.metadata.create_all(engine)  # create tables
    session_ = Session()
    yield session_
    session_.close()
    Based.metadata.drop_all(engine)  # drop tables


def test_query_tables(session):
    """Return a list of tables in the database."""
    table_names = query_tables(session)
    session.commit()

    np.testing.assert_array_equal(table_names, ["dropme", "verybased"])


def test_drop_table(session):
    """Drop a table from the database."""
    drop_table(session, "dropme")
    table_names = query_tables(session)
    session.commit()

    np.testing.assert_array_equal(table_names, ["verybased"])


class TestUserMapInterface:
    """Testing postgres interface for usermap table"""

    def test_get_user_map(self, session):
        """Testing retrevial of usermap via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        add_user_map(username=username_1, addresses=addresses_1, session=session)
        username_2 = "b"
        addresses_2 = ["4", "5"]
        add_user_map(username=username_2, addresses=addresses_2, session=session)

        # This is in order of insertion
        user_map_df = get_user_map(session)
        assert len(user_map_df) == 5
        np.testing.assert_array_equal(user_map_df["username"], ["a", "a", "a", "b", "b"])
        np.testing.assert_array_equal(user_map_df["address"], ["1", "2", "3", "4", "5"])

    def test_get_query_user_map(self, session):
        """Testing querying by block number of user map via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        add_user_map(username=username_1, addresses=addresses_1, session=session)
        username_2 = "b"
        addresses_2 = ["4", "5"]
        add_user_map(username=username_2, addresses=addresses_2, session=session)

        user_map_df = get_user_map(session, address="1")
        np.testing.assert_array_equal(user_map_df["username"], ["a"])
        user_map_df = get_user_map(session, address="2")
        np.testing.assert_array_equal(user_map_df["username"], ["a"])
        user_map_df = get_user_map(session, address="3")
        np.testing.assert_array_equal(user_map_df["username"], ["a"])
        user_map_df = get_user_map(session, address="4")
        np.testing.assert_array_equal(user_map_df["username"], ["b"])
        user_map_df = get_user_map(session, address="5")
        np.testing.assert_array_equal(user_map_df["username"], ["b"])

    def test_user_map_insertion_error(self, session):
        """Testing retrevial of usermap via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        add_user_map(username=username_1, addresses=addresses_1, session=session)

        # Adding the same addresses with the same username should pass
        username_2 = "a"
        addresses_2 = ["1", "2", "5"]
        add_user_map(username=username_2, addresses=addresses_2, session=session)

        user_map_df = get_user_map(session)
        assert len(user_map_df) == 4
        np.testing.assert_array_equal(user_map_df["username"], ["a", "a", "a", "a"])
        np.testing.assert_array_equal(user_map_df["address"], ["1", "2", "3", "5"])

        # Adding the same addresses with different username should fail
        username_3 = "b"
        addresses_3 = ["6", "1", "2", "4"]
        with pytest.raises(ValueError):
            add_user_map(username=username_3, addresses=addresses_3, session=session)

        # Final db values shouldn't change
        user_map_df = get_user_map(session)
        user_map_df = get_user_map(session)
        assert len(user_map_df) == 4
        np.testing.assert_array_equal(user_map_df["username"], ["a", "a", "a", "a"])
        np.testing.assert_array_equal(user_map_df["address"], ["1", "2", "3", "5"])
