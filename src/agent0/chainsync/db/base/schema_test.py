"""CRUD tests for UserMap"""

import pytest

from .schema import AddrToUsername


class TestAddrToUsernameTable:
    """CRUD tests for AddrToUsername table"""

    @pytest.mark.docker
    def test_create_addr_to_username(self, db_session):
        """Create and entry"""
        user_map = AddrToUsername(address="1", username="a")
        db_session.add(user_map)
        db_session.commit()

        retrieved_map = db_session.query(AddrToUsername).filter_by(address="1").first()
        assert retrieved_map is not None
        assert retrieved_map.username == "a"

    @pytest.mark.docker
    def test_update_addr_to_username(self, db_session):
        """Update an entry"""
        user_map = AddrToUsername(address="1", username="a")
        db_session.add(user_map)
        db_session.commit()

        user_map.username = "b"
        db_session.commit()

        updated_map = db_session.query(AddrToUsername).filter_by(address="1").first()
        assert updated_map.username == "b"

    @pytest.mark.docker
    def test_delete_addr_to_username(self, db_session):
        """Delete an entry"""
        user_map = AddrToUsername(address="1", username="a")
        db_session.add(user_map)
        db_session.commit()

        db_session.delete(user_map)
        db_session.commit()

        deleted_map = db_session.query(AddrToUsername).filter_by(address="1").first()
        assert deleted_map is None
