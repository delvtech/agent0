"""CRUD tests for CheckpointInfo"""
import numpy as np
import pytest
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, sessionmaker

from src.data import postgres

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
    table_names = postgres.query_tables(session)
    session.commit()

    np.testing.assert_array_equal(table_names, ["dropme", "verybased"])


def test_drop_table(session):
    """Drop a table from the database."""
    postgres.drop_table(session, "dropme")
    table_names = postgres.query_tables(session)
    session.commit()

    np.testing.assert_array_equal(table_names, ["verybased"])
