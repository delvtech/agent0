"""Python api interface for calling the flask server"""

import logging
import time
import warnings
from http import HTTPStatus
from io import StringIO

import pandas as pd
import requests


def register_username(api_uri: str, wallet_addrs: list[str], username: str) -> None:
    """Registers the username with the flask server.

    Arguments
    ---------
    api_uri: str
        The endpoint for the flask server.
    wallet_addrs: list[str]
        The list of wallet addresses to register.
    username: str
        The username to register the wallet addresses under.
    """
    # TODO: use the json schema from the server.
    json_data = {"wallet_addrs": wallet_addrs, "username": username}
    result = requests.post(f"{api_uri}/register_agents", json=json_data, timeout=3)
    if result.status_code != HTTPStatus.OK:
        raise ConnectionError(result)


def balance_of(api_uri: str, wallet_addrs: list[str]) -> pd.DataFrame:
    """Gets all open positions for a given list of wallet addresses from the db.

    Arguments
    ---------
    api_uri: str
        The endpoint for the flask server.
    wallet_addrs: list[str]
        The list of wallet addresses to register.

    Returns
    -------
    pd.DataFrame
        A DataFrame that consists of all open positions for the given wallet addresses.
    """
    # TODO: use the json schema from the server.
    json_data = {"wallet_addrs": wallet_addrs}
    result = None
    for _ in range(10):
        try:
            result = requests.post(f"{api_uri}/balance_of", json=json_data, timeout=3)
            break
        except requests.exceptions.RequestException:
            logging.warning("Connection error to db api server, retrying")
            time.sleep(1)
            continue

    if result is None or (result.status_code != HTTPStatus.OK):
        raise ConnectionError(result)

    # Read json and return
    # Since we use pandas write json, we use pandas read json to read, then adjust data
    # before returning
    # We explicitly set dtype to False to keep everything in string format
    # to avoid loss of precision
    # For some reason, pandas internally is throwing a warning about datetimes here,
    # we ignore
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        data = pd.read_json(StringIO(result.json()["data"]), dtype=False)
    return data
