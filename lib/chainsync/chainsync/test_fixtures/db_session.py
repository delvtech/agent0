"""Pytest fixture that creates an in memory db session and creates the base db schema"""
from typing import Any, Generator

import pytest
from chainsync.db.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, Any, Any]:
    """Initializes the in memory db session and creates the db schema"""
    engine = create_engine("sqlite:///:memory:")  # in-memory SQLite database for testing
    session = sessionmaker(bind=engine)

    Base.metadata.create_all(engine)  # create tables
    db_session_ = session()
    yield db_session_
    db_session_.close()
    Base.metadata.drop_all(engine)  # drop tables
