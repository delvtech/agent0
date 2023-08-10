import pytest
from sqlalchemy import String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, MappedAsDataclass, mapped_column, sessionmaker


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
def dummy_session():
    engine = create_engine("sqlite:///:memory:")  # in-memory SQLite database for testing
    Session = sessionmaker(bind=engine)
    """Dummy session fixture for tests"""
    DummyBase.metadata.create_all(engine)  # create tables
    test_session_ = Session()
    yield test_session_
    test_session_.close()
    DummyBase.metadata.drop_all(engine)  # drop tables
