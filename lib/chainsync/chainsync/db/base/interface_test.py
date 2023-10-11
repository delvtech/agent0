"""CRUD tests for CheckpointInfo"""
import numpy as np
import pytest

from .interface import add_user_map, drop_table, get_addr_to_username, query_tables


def test_query_tables(dummy_session):
    """Return a list of tables in the database."""
    table_names = query_tables(dummy_session)
    dummy_session.commit()

    np.testing.assert_array_equal(table_names, ["dropme", "verybased"])


def test_drop_table(dummy_session):
    """Drop a table from the database."""
    drop_table(dummy_session, "dropme")
    table_names = query_tables(dummy_session)
    dummy_session.commit()

    np.testing.assert_array_equal(table_names, ["verybased"])


class TestUserMapInterface:
    """Testing postgres interface for usermap table"""

    def test_get_user_map(self, db_session):
        """Testing retrevial of usermap via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        add_user_map(username=username_1, addresses=addresses_1, session=db_session)
        username_2 = "b"
        addresses_2 = ["4", "5"]
        add_user_map(username=username_2, addresses=addresses_2, session=db_session)

        # This is in order of insertion
        user_map_df = get_addr_to_username(db_session)
        assert len(user_map_df) == 5
        np.testing.assert_array_equal(user_map_df["username"], ["a", "a", "a", "b", "b"])
        np.testing.assert_array_equal(user_map_df["address"], ["1", "2", "3", "4", "5"])

    def test_get_query_user_map(self, db_session):
        """Testing querying by block number of user map via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        add_user_map(username=username_1, addresses=addresses_1, session=db_session)
        username_2 = "b"
        addresses_2 = ["4", "5"]
        add_user_map(username=username_2, addresses=addresses_2, session=db_session)

        user_map_df = get_addr_to_username(db_session, address="1")
        np.testing.assert_array_equal(user_map_df["username"], ["a"])
        user_map_df = get_addr_to_username(db_session, address="2")
        np.testing.assert_array_equal(user_map_df["username"], ["a"])
        user_map_df = get_addr_to_username(db_session, address="3")
        np.testing.assert_array_equal(user_map_df["username"], ["a"])
        user_map_df = get_addr_to_username(db_session, address="4")
        np.testing.assert_array_equal(user_map_df["username"], ["b"])
        user_map_df = get_addr_to_username(db_session, address="5")
        np.testing.assert_array_equal(user_map_df["username"], ["b"])

    def test_user_map_insertion_error(self, db_session):
        """Testing retrevial of usermap via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        add_user_map(username=username_1, addresses=addresses_1, session=db_session)

        # Adding the same addresses with the same username should pass
        username_2 = "a"
        addresses_2 = ["1", "2", "5"]
        add_user_map(username=username_2, addresses=addresses_2, session=db_session)

        user_map_df = get_addr_to_username(db_session)
        assert len(user_map_df) == 4
        np.testing.assert_array_equal(user_map_df["username"], ["a", "a", "a", "a"])
        np.testing.assert_array_equal(user_map_df["address"], ["1", "2", "3", "5"])

        # Adding the same addresses with different username should fail
        username_3 = "b"
        addresses_3 = ["6", "1", "2", "4"]
        with pytest.raises(ValueError):
            add_user_map(username=username_3, addresses=addresses_3, session=db_session)

        # Final db values shouldn't change
        user_map_df = get_addr_to_username(db_session)
        user_map_df = get_addr_to_username(db_session)
        assert len(user_map_df) == 4
        np.testing.assert_array_equal(user_map_df["username"], ["a", "a", "a", "a"])
        np.testing.assert_array_equal(user_map_df["address"], ["1", "2", "3", "5"])
