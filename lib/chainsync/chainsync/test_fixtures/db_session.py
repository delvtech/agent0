"""Pytest fixture that creates an in memory db session and creates the base db schema"""
import os
import subprocess
import time
from pathlib import Path
from typing import Iterator
import logging

import docker
import pytest
from chainsync import PostgresConfig
from chainsync.db.base import Base, initialize_engine
from pytest_postgresql.janitor import DatabaseJanitor
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

# fixture arguments in test function have to be the same as the fixture name
# pylint: disable=redefined-outer-name


@pytest.fixture(scope="session")
def psql_docker() -> Iterator[PostgresConfig]:
    """Test fixture for running postgres in docker

    Returns
    -------
    Iterator[PostgresConfig]
        An iterator that yields a PostgresConfig
    """
    home_dir = os.path.expanduser("~")
    socket_path = Path(f"{home_dir}/.docker/desktop/docker.sock")
    if socket_path.exists():
        logging.debug("The socket exists at %s.. using it to connect to docker", socket_path)
        client = docker.DockerClient(base_url=f"unix://{socket_path}")
    else:
        logging.debug("No socket found at %s.. using default socket", socket_path)
        client = docker.from_env()

    # Using these config for tests
    postgres_config = PostgresConfig(
        POSTGRES_USER="admin",
        POSTGRES_PASSWORD="password",
        POSTGRES_DB="postgres_db_test",
        POSTGRES_HOST="127.0.0.1",
        POSTGRES_PORT=5555,
    )

    container = client.containers.run(
        image="postgres",
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
    time.sleep(3)

    yield postgres_config

    # Docker doesn't play nice with types
    container.kill()  # type:ignore


@pytest.fixture(scope="session")
def database_engine(psql_docker: PostgresConfig) -> Iterator[Engine]:
    """Test fixture creating psql engine on local postgres container

    Arguments
    ---------
    psql_docker: PostgresConfig
        The PostgresConfig object returned by the `psql_docker` test fixture

    Returns
    -------
    Iterator[Engine]
        An iterator that yields a sqlalchemy engine
    """
    # Using default postgres info
    # Renaming variable to match what it actually is, i.e., the postgres config
    postgres_config = psql_docker
    with DatabaseJanitor(
        user=postgres_config.POSTGRES_USER,
        host="127.0.0.1",
        port=postgres_config.POSTGRES_PORT,
        dbname=postgres_config.POSTGRES_DB,
        version="latest",
        password=postgres_config.POSTGRES_PASSWORD,
    ):
        engine = initialize_engine(postgres_config)
        yield engine


@pytest.fixture(scope="function")
def db_session(database_engine: Engine) -> Iterator[Session]:
    """Initializes the in memory db session and creates the db schema

    Arguments
    ---------
    database_engine : Engine
        The sqlalchemy database engine returned from the `database_engine` test fixture

    Returns
    -------
    Iterator[Session]
        Yields the sqlalchemy session object
    """

    session = sessionmaker(bind=database_engine)

    Base.metadata.create_all(database_engine)  # create tables
    db_session_ = session()

    yield db_session_

    db_session_.close()
    Base.metadata.drop_all(database_engine)  # drop tables


@pytest.fixture(scope="function")
def db_api(psql_docker: PostgresConfig) -> Iterator[str]:
    """Launches a process for the db api

    Arguments
    ---------
    psql_docker: PostgresConfig
        The PostgresConfig object returned by the `psql_docker` test fixture

    Returns
    -------
    Iterator[str]
        Yields the database api uri
    """
    # Launch the database api server here
    db_api_host = "127.0.0.1"
    db_api_port = 5005

    api_server_path = Path(__file__).parent.joinpath("../db/api/api_server")

    # Modify an environment to set db credentials
    env = os.environ.copy()
    # Set all env variables from the psql docker config
    env["POSTGRES_USER"] = psql_docker.POSTGRES_USER
    env["POSTGRES_PASSWORD"] = psql_docker.POSTGRES_PASSWORD
    env["POSTGRES_DB"] = psql_docker.POSTGRES_DB
    env["POSTGRES_HOST"] = psql_docker.POSTGRES_HOST
    env["POSTGRES_PORT"] = str(psql_docker.POSTGRES_PORT)

    # Pass db credentials via env vars
    # Since this is a forever running service, we explicitly kill after the yield returns
    # pylint: disable=consider-using-with
    api_process = subprocess.Popen(
        ["flask", "--app", api_server_path, "run", "--host", db_api_host, "--port", str(db_api_port)], env=env
    )

    yield "http://" + db_api_host + ":" + str(db_api_port)

    api_process.kill()
