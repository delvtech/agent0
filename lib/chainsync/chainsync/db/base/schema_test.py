"""CRUD tests for UserMap"""
from .schema import AddrToUsername, UsernameToUser


class TestAddrToUsernameTable:
    """CRUD tests for AddrToUsername table"""

    def test_create_addr_to_username(self, db_session):
        """Create and entry"""
        user_map = AddrToUsername(address="1", username="a")
        db_session.add(user_map)
        db_session.commit()

        retrieved_map = db_session.query(AddrToUsername).filter_by(address="1").first()
        assert retrieved_map is not None
        assert retrieved_map.username == "a"

    def test_update_addr_to_username(self, db_session):
        """Update an entry"""
        user_map = AddrToUsername(address="1", username="a")
        db_session.add(user_map)
        db_session.commit()

        user_map.username = "b"
        db_session.commit()

        updated_map = db_session.query(AddrToUsername).filter_by(address="1").first()
        assert updated_map.username == "b"

    def test_delete_addr_to_username(self, db_session):
        """Delete an entry"""
        user_map = AddrToUsername(address="1", username="a")
        db_session.add(user_map)
        db_session.commit()

        db_session.delete(user_map)
        db_session.commit()

        deleted_map = db_session.query(AddrToUsername).filter_by(address="1").first()
        assert deleted_map is None


class TestUsernameToUserTable:
    """CRUD tests for UsernameToUser table"""

    def test_create_username_to_user(self, db_session):
        """Create and entry"""
        user_map = UsernameToUser(username="a", user="1")
        db_session.add(user_map)
        db_session.commit()

        retrieved_map = db_session.query(UsernameToUser).filter_by(username="a").first()
        assert retrieved_map is not None
        assert retrieved_map.user == "1"

    def test_update_username_to_user(self, db_session):
        """Update an entry"""
        user_map = UsernameToUser(username="a", user="1")
        db_session.add(user_map)
        db_session.commit()

        user_map.user = "2"
        db_session.commit()

        updated_map = db_session.query(UsernameToUser).filter_by(username="a").first()
        assert updated_map.user == "2"

    def test_delete_username_to_user(self, db_session):
        """Delete an entry"""
        user_map = UsernameToUser(username="a", user="1")
        db_session.add(user_map)
        db_session.commit()

        db_session.delete(user_map)
        db_session.commit()

        deleted_map = db_session.query(UsernameToUser).filter_by(username="a").first()
        assert deleted_map is None
