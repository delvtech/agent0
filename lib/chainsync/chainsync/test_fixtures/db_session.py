import pytest
from chainsync.db.base import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture(scope="function")
def db_session():
    """Initializes the in memory db session and creates the db schema"""
    engine = create_engine("sqlite:///:memory:")  # in-memory SQLite database for testing
    Session = sessionmaker(bind=engine)

    Base.metadata.create_all(engine)  # create tables
    db_session_ = Session()
    yield db_session_
    db_session_.close()
    Base.metadata.drop_all(engine)  # drop tables
