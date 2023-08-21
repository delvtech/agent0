"""CRUD tests for UserMap"""
# Ignoring unused import warning, fixtures are used through variable name
from chainsync.test_fixtures import db_session  # pylint: disable=unused-import

from .schema import UserMap

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name


class TestUserMapTable:
    """CRUD tests for UserMap table"""

    def test_create_user_map(self, db_session):
        """Create and entry"""
        user_map = UserMap(address="1", username="a")
        db_session.add(user_map)
        db_session.commit()

        retrieved_user_map = db_session.query(UserMap).filter_by(address="1").first()
        assert retrieved_user_map is not None
        assert retrieved_user_map.username == "a"

    def test_update_user_map(self, db_session):
        """Update an entry"""
        user_map = UserMap(address="1", username="a")
        db_session.add(user_map)
        db_session.commit()

        user_map.username = "b"
        db_session.commit()

        updated_user_map = db_session.query(UserMap).filter_by(address="1").first()
        # tokenValue retrieved from postgres is in Decimal, cast to float
        assert updated_user_map.username == "b"

    def test_delete_user_map(self, db_session):
        """Delete an entry"""
        user_map = UserMap(address="1", username="a")
        db_session.add(user_map)
        db_session.commit()

        db_session.delete(user_map)
        db_session.commit()

        deleted_user_map = db_session.query(UserMap).filter_by(address="1").first()
        assert deleted_user_map is None
