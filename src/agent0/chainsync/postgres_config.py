"""Defines the postgres configuration from env vars."""

from __future__ import annotations

import os
from dataclasses import dataclass

from dotenv import load_dotenv
from sqlalchemy import URL


@dataclass
class PostgresConfig:
    """The configuration dataclass for postgres connections.

    Replace the user, password, and db_name with the credentials of your setup.
    """

    # default values for local postgres
    # Matching environment variables to search for
    # pylint: disable=invalid-name
    POSTGRES_USER: str = "admin"
    """The username to authenticate with."""
    POSTGRES_PASSWORD: str = "password"
    """The password to authenticate with."""
    POSTGRES_DB: str = "agent0_db"
    """The name of the database."""
    POSTGRES_HOST: str = "localhost"
    """The hostname to connect to."""
    POSTGRES_PORT: int = 5432
    """The port to connect to."""
    POSTGRES_VERSION: str | None = None
    """The postgres version."""

    def create_url_obj(self) -> URL:
        """Creates an SQLAlchemy URL object from the config.

        Returns
        -------
        URL
            An SQLAlchemy URL object.
        """
        return URL.create(
            drivername="postgresql+psycopg",
            username=self.POSTGRES_USER,
            password=self.POSTGRES_PASSWORD,
            host=self.POSTGRES_HOST,
            port=self.POSTGRES_PORT,
            database=self.POSTGRES_DB,
        )


def build_postgres_config_from_env() -> PostgresConfig:
    """Build a PostgresConfig that looks for environmental variables.
    If env var exists, use that, otherwise, use default.

    Returns
    -------
    PostgresConfig
        Config settings required to connect to and use the database.
    """
    # Look for and load local config if it exists
    load_dotenv(".env")

    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    database = os.getenv("POSTGRES_DB")
    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT")

    arg_dict = {}
    if user is not None:
        arg_dict["POSTGRES_USER"] = user
    if password is not None:
        arg_dict["POSTGRES_PASSWORD"] = password
    if database is not None:
        arg_dict["POSTGRES_DB"] = database
    if host is not None:
        arg_dict["POSTGRES_HOST"] = host
    if port is not None:
        arg_dict["POSTGRES_PORT"] = int(port)

    return PostgresConfig(**arg_dict)
