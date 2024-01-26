"""Pytest fixture that creates an in memory db session and creates dummy db schemas"""

from typing import Iterator

import pytest
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, Session, mapped_column, sessionmaker


class DummyBase(MappedAsDataclass, DeclarativeBase):
    """Base class to subclass from to define the schema"""


class Very(DummyBase):
    """Dummy but very sincere table schema."""

    __tablename__ = "verybased"

    key: Mapped[str] = mapped_column(String, primary_key=True)


class DropMe(DummyBase):
    """Dummy table schema that wants to be dropped."""

    __tablename__ = "dropme"

    key: Mapped[str] = mapped_column(String, primary_key=True)


@pytest.fixture(scope="function")
def dummy_session() -> Iterator[Session]:
    """Dummy session fixture for tests.

    Yields
    -------
    Session
        A sqlalchemy session object
    """
    engine = create_engine("sqlite:///:memory:")  # in-memory SQLite database for testing
    session = sessionmaker(bind=engine)
    DummyBase.metadata.create_all(engine)  # create tables
    test_session_ = session()
    yield test_session_
    test_session_.close()
    DummyBase.metadata.drop_all(engine)  # drop tables
