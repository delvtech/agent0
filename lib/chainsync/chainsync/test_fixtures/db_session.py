"""Pytest fixture that creates an in memory db session and creates the base db schema"""
import time
from typing import Any, Iterator

import docker
import pytest
from chainsync import PostgresConfig
from chainsync.db.base import Base, initialize_engine
from pytest_postgresql.janitor import DatabaseJanitor
from sqlalchemy.orm import Session, sessionmaker

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name


@pytest.fixture(scope="session")
def psql_docker() -> Iterator[PostgresConfig]:
    """Test fixture for running postgres in docker"""
    client = docker.from_env()

    # Using these config for tests
    postgres_config = PostgresConfig(
        POSTGRES_USER="admin",
        POSTGRES_PASSWORD="password",
        POSTGRES_DB="postgres_db_test",
        POSTGRES_HOST="localhost",
        POSTGRES_PORT=5555,
    )

    container = client.containers.run(
        image="postgres:12",
        auto_remove=True,
        environment={
            "POSTGRES_USER": postgres_config.POSTGRES_USER,
            "POSTGRES_PASSWORD": postgres_config.POSTGRES_PASSWORD,
        },
        name="test_postgres",
        ports={"5432/tcp": ("127.0.0.1", postgres_config.POSTGRES_PORT)},
        detach=True,
        remove=True,
    )

    # Wait for the container to start
    time.sleep(5)

    yield postgres_config

    # Docker doesn't play nice with types
    container.stop()  # type:ignore


@pytest.fixture(scope="session")
def database_engine(psql_docker):
    """Test fixture creating psql engine on local postgres container"""
    # Using default postgres info
    # Renaming variable to match what it actually is, i.e., the postgres config
    postgres_config = psql_docker
    with DatabaseJanitor(
        user=postgres_config.POSTGRES_USER,
        host="localhost",
        port=postgres_config.POSTGRES_PORT,
        dbname=postgres_config.POSTGRES_DB,
        version=12,
        password=postgres_config.POSTGRES_PASSWORD,
    ):
        engine = initialize_engine(postgres_config)
        yield engine


@pytest.fixture(scope="function")
def db_session(database_engine) -> Iterator[Session]:
    """Initializes the in memory db session and creates the db schema"""
    session = sessionmaker(bind=database_engine)

    Base.metadata.create_all(database_engine)  # create tables
    db_session_ = session()
    yield db_session_
    db_session_.close()
    Base.metadata.drop_all(database_engine)  # drop tables
