"""CRUD tests for CheckpointInfo"""

import numpy as np
import pytest

from .interface import (
    add_addr_to_username,
    add_username_to_user,
    drop_table,
    get_addr_to_username,
    get_username_to_user,
    query_tables,
)


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


class TestAddrToUsernameInterface:
    """Testing postgres interface for usermap table"""

    @pytest.mark.docker
    def test_get_addr_to_username(self, db_session):
        """Testing retrieval of usernames via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        add_addr_to_username(username=username_1, addresses=addresses_1, session=db_session)
        username_2 = "b"
        addresses_2 = ["4", "5"]
        add_addr_to_username(username=username_2, addresses=addresses_2, session=db_session)
        # Single string insertion
        username_3 = "c"
        addresses_3 = "6"
        add_addr_to_username(username=username_3, addresses=addresses_3, session=db_session)

        user_map_df = get_addr_to_username(db_session)
        assert len(user_map_df) == 6
        # Sort by usernames, then address to ensure order
        user_map_df = user_map_df.sort_values(["username", "address"], axis=0)
        np.testing.assert_array_equal(user_map_df["username"], ["a", "a", "a", "b", "b", "c"])
        np.testing.assert_array_equal(user_map_df["address"], ["1", "2", "3", "4", "5", "6"])

    @pytest.mark.docker
    def test_get_query_address(self, db_session):
        """Testing querying by address of addr_to_username via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        add_addr_to_username(username=username_1, addresses=addresses_1, session=db_session)
        username_2 = "b"
        addresses_2 = ["4", "5"]
        add_addr_to_username(username=username_2, addresses=addresses_2, session=db_session)

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

    @pytest.mark.docker
    def test_addr_to_username_insertion_error(self, db_session):
        """Testing insertion conflicts of addr_to_username via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        add_addr_to_username(username=username_1, addresses=addresses_1, session=db_session)

        # Adding the same addresses with the same username should pass
        username_2 = "a"
        addresses_2 = ["1", "2", "5"]
        add_addr_to_username(username=username_2, addresses=addresses_2, session=db_session)

        user_map_df = get_addr_to_username(db_session)
        assert len(user_map_df) == 4
        # Sort by usernames, then address to ensure order
        user_map_df = user_map_df.sort_values(["username", "address"], axis=0)
        np.testing.assert_array_equal(user_map_df["username"], ["a", "a", "a", "a"])
        np.testing.assert_array_equal(user_map_df["address"], ["1", "2", "3", "5"])

        # Adding the same addresses with different username should fail
        # The add_addr_to_username is all or nothing, so if one fails, all fails
        username_3 = "b"
        addresses_3 = ["6", "1", "2", "4"]
        with pytest.raises(ValueError):
            add_addr_to_username(username=username_3, addresses=addresses_3, session=db_session)

        # Final db values shouldn't change
        user_map_df = get_addr_to_username(db_session)
        assert len(user_map_df) == 4
        # Sort by usernames, then address to ensure order
        user_map_df = user_map_df.sort_values(["username", "address"], axis=0)
        np.testing.assert_array_equal(user_map_df["username"], ["a", "a", "a", "a"])
        np.testing.assert_array_equal(user_map_df["address"], ["1", "2", "3", "5"])

    @pytest.mark.docker
    def test_addr_to_username_force_insertion(self, db_session):
        """Testing force insertion of addr_to_username via interface"""
        username_1 = "a"
        addresses_1 = ["1", "2", "3"]
        add_addr_to_username(username=username_1, addresses=addresses_1, session=db_session)

        # Adding the same addresses with different username with force update should update the row
        username_2 = "b"
        addresses_2 = ["6", "1", "2", "4"]
        add_addr_to_username(username=username_2, addresses=addresses_2, session=db_session, force_update=True)

        # Final db values should reflect most recently updated
        user_map_df = get_addr_to_username(db_session)
        assert len(user_map_df) == 5
        # Sort by usernames, then address to ensure order
        user_map_df = user_map_df.sort_values(["username", "address"], axis=0)
        np.testing.assert_array_equal(user_map_df["username"], ["a", "b", "b", "b", "b"])
        np.testing.assert_array_equal(user_map_df["address"], ["3", "1", "2", "4", "6"])


class TestUserToUsernameInterface:
    """Testing postgres interface for usermap table"""

    @pytest.mark.docker
    def test_get_user_to_username(self, db_session):
        """Testing retrieval of usernames via interface"""
        user_1 = "1"
        username_1 = "a"
        add_username_to_user(user=user_1, username=username_1, session=db_session)
        user_2 = "2"
        username_2 = "b"
        add_username_to_user(user=user_2, username=username_2, session=db_session)
        # Many to one mapping
        user_3 = "2"
        username_3 = "c"
        add_username_to_user(user=user_3, username=username_3, session=db_session)

        user_map_df = get_username_to_user(db_session)
        assert len(user_map_df) == 3
        # Sort by usernames, then user to ensure order
        user_map_df = user_map_df.sort_values(["username", "user"], axis=0)
        np.testing.assert_array_equal(user_map_df["username"], ["a", "b", "c"])
        np.testing.assert_array_equal(user_map_df["user"], ["1", "2", "2"])

    @pytest.mark.docker
    def test_get_query_username(self, db_session):
        """Testing querying by username of username_to_user via interface"""
        user_1 = "1"
        username_1 = "a"
        add_username_to_user(user=user_1, username=username_1, session=db_session)
        user_2 = "2"
        username_2 = "b"
        add_username_to_user(user=user_2, username=username_2, session=db_session)
        # Many to one mapping
        user_3 = "2"
        username_3 = "c"
        add_username_to_user(user=user_3, username=username_3, session=db_session)

        user_map_df = get_username_to_user(db_session, username="a")
        np.testing.assert_array_equal(user_map_df["user"], ["1"])
        user_map_df = get_username_to_user(db_session, username="b")
        np.testing.assert_array_equal(user_map_df["user"], ["2"])
        user_map_df = get_username_to_user(db_session, username="c")
        np.testing.assert_array_equal(user_map_df["user"], ["2"])

    @pytest.mark.docker
    def test_username_to_user_insertion_error(self, db_session):
        """Testing insertion conflicts of username_to_user via interface"""
        user_1 = "1"
        username_1 = "a"
        add_username_to_user(user=user_1, username=username_1, session=db_session)
        user_2 = "2"
        username_2 = "b"
        add_username_to_user(user=user_2, username=username_2, session=db_session)
        # Many to one mapping
        user_3 = "2"
        username_3 = "c"
        add_username_to_user(user=user_3, username=username_3, session=db_session)

        # Adding the same username with the same user should pass
        user_4 = "2"
        username_4 = "b"
        add_username_to_user(user=user_4, username=username_4, session=db_session)

        user_map_df = get_username_to_user(db_session)
        assert len(user_map_df) == 3
        # Sort by usernames, then address to ensure order
        user_map_df = user_map_df.sort_values(["username", "user"], axis=0)
        np.testing.assert_array_equal(user_map_df["username"], ["a", "b", "c"])
        np.testing.assert_array_equal(user_map_df["user"], ["1", "2", "2"])

        # Adding the same username with different user should fail
        user_5 = "6"
        username_5 = "b"
        with pytest.raises(ValueError):
            add_username_to_user(user=user_5, username=username_5, session=db_session)

        # Final db values shouldn't change
        user_map_df = get_username_to_user(db_session)
        assert len(user_map_df) == 3
        # Sort by usernames, then address to ensure order
        user_map_df = user_map_df.sort_values(["username", "user"], axis=0)
        np.testing.assert_array_equal(user_map_df["username"], ["a", "b", "c"])
        np.testing.assert_array_equal(user_map_df["user"], ["1", "2", "2"])

    @pytest.mark.docker
    def test_addr_to_username_force_insertion(self, db_session):
        """Testing force insertion of addr_to_username via interface"""
        user_1 = "1"
        username_1 = "a"
        add_username_to_user(user=user_1, username=username_1, session=db_session)
        user_2 = "2"
        username_2 = "b"
        add_username_to_user(user=user_2, username=username_2, session=db_session)
        # Many to one mapping
        user_3 = "2"
        username_3 = "c"
        add_username_to_user(user=user_3, username=username_3, session=db_session)

        # Adding the same addresses with different username with force update should update the row
        user_4 = "6"
        username_4 = "b"
        add_username_to_user(user=user_4, username=username_4, session=db_session, force_update=True)

        # Final db values should reflect most recently updated
        user_map_df = get_username_to_user(db_session)
        assert len(user_map_df) == 3
        # Sort by usernames, then address to ensure order
        user_map_df = user_map_df.sort_values(["username", "user"], axis=0)
        np.testing.assert_array_equal(user_map_df["username"], ["a", "b", "c"])
        np.testing.assert_array_equal(user_map_df["user"], ["1", "6", "2"])
