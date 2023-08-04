"""Helper class for storing Hyperdrive addresses"""
from __future__ import annotations

import logging
import re
import time

import attr
import requests


@attr.s
class HyperdriveAddresses:
    """Addresses for deployed Hyperdrive contracts."""

    # pylint: disable=too-few-public-methods

    base_token: str = attr.ib()
    hyperdrive_factory: str = attr.ib()
    mock_hyperdrive: str = attr.ib()
    mock_hyperdrive_math: str = attr.ib()


def fetch_hyperdrive_address_from_url(contracts_url: str) -> HyperdriveAddresses:
    """Fetch addresses for deployed contracts in the Hyperdrive system."""
    response = None
    for _ in range(100):
        response = requests.get(contracts_url, timeout=60)
        # Check the status code and retry the request if it fails
        if response.status_code != 200:
            logging.warning(
                "Request for contracts_url=%s failed with status code %s @ %s",
                contracts_url,
                response.status_code,
                time.ctime(),
            )
            time.sleep(10)
            continue
        # If successful, exit attempt loop
        break
    if response is None:
        raise ConnectionError("Request failed, returning status `None`")
    if response.status_code != 200:
        raise ConnectionError(f"Request failed with status code {response.status_code} @ {time.ctime()}")
    addresses_json = response.json()

    def camel_to_snake(snake_string: str) -> str:
        return re.sub(r"(?<!^)(?=[A-Z])", "_", snake_string).lower()

    addresses = HyperdriveAddresses(**{camel_to_snake(key): value for key, value in addresses_json.items()})
    return addresses
