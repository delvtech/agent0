"""Defines the postgres configuration from env vars."""

import os
from dataclasses import dataclass

from dotenv import load_dotenv


@dataclass
class PostgresConfig:
    """The configuration dataclass for postgres connections.

    Replace the user, password, and db_name with the credentials of your setup.

    Attributes
    ----------
    POSTGRES_USER : str
        The username to authenticate with
    POSTGRES_PASSWORD : str
        The password to authenticate with
    POSTGRES_DB : str
        The name of the database
    POSTGRES_HOST : str
        The hostname to connect to
    POSTGRES_PORT : int
        The port to connect to
    """

    # default values for local postgres
    # Matching environment variables to search for
    # pylint: disable=invalid-name
    POSTGRES_USER: str = "admin"
    POSTGRES_PASSWORD: str = "password"
    POSTGRES_DB: str = "postgres_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432


def build_postgres_config() -> PostgresConfig:
    """Build a PostgresConfig that looks for environmental variables.

    If env var exists, use that, otherwise, default

    Returns
    -------
    config : PostgresConfig
        Config settings required to connect to and use the database
    """
    # Look for and load local config if it exists
    load_dotenv("postgres.env")

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
