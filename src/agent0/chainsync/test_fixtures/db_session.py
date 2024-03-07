"""Create an in memory db session and creates the base db schema."""

import logging
import os
import re
import subprocess
import time
from pathlib import Path
from typing import Iterator

import docker
import pytest
from docker.errors import APIError, DockerException, NotFound
from docker.models.containers import Container
from pytest_postgresql.janitor import DatabaseJanitor
from sqlalchemy import Engine
from sqlalchemy.orm import Session, sessionmaker

from agent0.chainsync import PostgresConfig
from agent0.chainsync.db.base import Base, initialize_engine

TEST_POSTGRES_NAME = "postgres_test"


@pytest.fixture(scope="session")
def psql_docker() -> Iterator[PostgresConfig]:
    """Test fixture for running postgres in docker.

    Yields
    -------
    PostgresConfig
        The PostgresConfig.
    """
    # Attempt to use the default socket if it exists
    try:
        try:
            client = docker.from_env()
        except Exception:  # pylint: disable=broad-exception-caught
            home_dir = os.path.expanduser("~")
            socket_path = Path(f"{home_dir}") / ".docker" / "desktop" / "docker.sock"
            if socket_path.exists():
                logging.debug("Docker not found at default socket, using %s..", socket_path)
                client = docker.DockerClient(base_url=f"unix://{socket_path}")
            else:
                logging.debug("Docker not found.")
                client = docker.from_env()
    # Skip this test if docker isn't installed
    except DockerException as exc:
        # This env variable gets set when running tests in CI
        # Hence, we don't want to skip this test if we're in CI
        in_ci = os.getenv("IN_CI")
        if in_ci is None:
            pytest.skip("Docker engine not found, skipping")
        else:
            raise exc

    # Using these config for tests
    postgres_config = PostgresConfig(
        POSTGRES_USER="admin",
        POSTGRES_PASSWORD="password",
        POSTGRES_DB="postgres_db_test",
        POSTGRES_HOST="127.0.0.1",
        POSTGRES_PORT=5555,
    )

    # Kill the test container if it already exists
    try:
        existing_container = client.containers.get(TEST_POSTGRES_NAME)
        assert isinstance(existing_container, Container)
    except NotFound:
        # Container doesn't exist, ignore
        existing_container = None
    if existing_container is not None:
        existing_container.remove(v=True, force=True)

    container = client.containers.run(
        image="postgres",
        auto_remove=True,
        environment={
            "POSTGRES_USER": postgres_config.POSTGRES_USER,
            "POSTGRES_PASSWORD": postgres_config.POSTGRES_PASSWORD,
        },
        name=TEST_POSTGRES_NAME,
        ports={"5432/tcp": ("127.0.0.1", postgres_config.POSTGRES_PORT)},
        detach=True,
        remove=True,
    )
    assert isinstance(container, Container)

    # Get version of postgres, retry until we get a response
    connected = False
    version_out = ""
    for _ in range(10):
        try:
            version_out = container.exec_run("postgres -V")[1]
            connected = True
            break
        except APIError:
            logging.warning("No postgres connection, retrying")
            time.sleep(1)
    if not connected:
        raise ValueError("Could not find postgres version")
    postgres_version = re.search(r"[0-9]+\.[0-9]+", str(version_out))
    if postgres_version is None:
        raise ValueError("Could not find postgres version")
    postgres_config.POSTGRES_VERSION = postgres_version[0]

    yield postgres_config

    # Remove the container along with volume
    container.kill()
    # Prune volumes
    client.volumes.prune()


@pytest.fixture(scope="session")
def database_engine(psql_docker: PostgresConfig) -> Iterator[Engine]:  # pylint: disable=redefined-outer-name
    """Create psql engine on local postgres container.

    Arguments
    ---------
    psql_docker: PostgresConfig
        The PostgresConfig object returned by the `psql_docker` test fixture.

    Yields
    -------
    Engine
        The sqlalchemy engine.
    """
    # Using default postgres info
    # Renaming variable to match what it actually is, i.e., the postgres config
    postgres_config = psql_docker
    if postgres_config.POSTGRES_VERSION is None:
        postgres_config.POSTGRES_VERSION = "latest"

    with DatabaseJanitor(
        user=postgres_config.POSTGRES_USER,
        host="127.0.0.1",
        port=postgres_config.POSTGRES_PORT,
        dbname=postgres_config.POSTGRES_DB,
        version=postgres_config.POSTGRES_VERSION,
        password=postgres_config.POSTGRES_PASSWORD,
    ):
        yield initialize_engine(postgres_config)


@pytest.fixture(scope="function")
def db_session(database_engine: Engine) -> Iterator[Session]:  # pylint: disable=redefined-outer-name
    """Initialize the in memory db session and creates the db schema.

    Arguments
    ---------
    database_engine: Engine
        The sqlalchemy database engine returned from the `database_engine` test fixture.

    Yields
    -------
    Session
        The sqlalchemy session object.
    """
    session = sessionmaker(bind=database_engine)

    Base.metadata.create_all(database_engine)  # create tables
    db_session_ = session()

    yield db_session_

    db_session_.close()
    Base.metadata.drop_all(database_engine)  # drop tables


@pytest.fixture(scope="session")
def db_api(psql_docker: PostgresConfig) -> Iterator[str]:  # pylint: disable=redefined-outer-name
    """Launch a process for the db api.

    Arguments
    ---------
    psql_docker: PostgresConfig
        The PostgresConfig object returned by the `psql_docker` test fixture

    Yields
    -------
    str
        The database api uri
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

    yield f"http://{db_api_host}:{db_api_port}"

    api_process.kill()
