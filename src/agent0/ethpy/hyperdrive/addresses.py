"""Helper class for storing Hyperdrive addresses"""

from __future__ import annotations

import logging
import time

import requests
from eth_typing import ChecksumAddress
from web3 import Web3

from agent0.hypertypes.utilities.conversions import camel_to_snake


def fetch_hyperdrive_addresses_from_uri(contracts_uri: str) -> dict[str, ChecksumAddress]:
    """Fetch addresses for deployed contracts in the Hyperdrive system.

    Arguments
    ---------
    contracts_uri: str
        The URI for the artifacts endpoint.

    Returns
    -------
    HyperdriveAddresses
        The addresses for deployed Hyperdrive contracts.
    """
    response = None
    for _ in range(100):
        response = requests.get(contracts_uri, timeout=60)
        # Check the status code and retry the request if it fails
        if response.status_code != 200:
            logging.warning(
                "Request for contracts_uri=%s failed with status code %s @ %s",
                contracts_uri,
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

    # We use a dictionary here to allow for dynamically generating deployed pools
    # without having to change the code here
    hyperdrive_addresses: dict[str, ChecksumAddress] = {}
    for key, value in addresses_json.items():
        # We don't add the base token or factory in the resulting addresses
        if key not in ("baseToken", "factory", "hyperdriveRegistry"):
            # We ensure checksum addresses here
            hyperdrive_addresses[camel_to_snake(key)] = Web3.to_checksum_address(value)

    return hyperdrive_addresses
