"""Helper class for storing Hyperdrive addresses"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass

import requests
from eth_typing import Address, ChecksumAddress

from agent0.hypertypes.utilities.conversions import camel_to_snake


@dataclass(kw_only=True)
class HyperdriveAddresses:
    """Addresses for deployed Hyperdrive contracts."""

    # pylint: disable=too-few-public-methods

    base_token: Address | ChecksumAddress
    erc4626_hyperdrive: Address | ChecksumAddress
    factory: Address | ChecksumAddress
    steth_hyperdrive: Address | ChecksumAddress


def fetch_hyperdrive_address_from_uri(contracts_uri: str) -> HyperdriveAddresses:
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

    # mockHyperdriveMath still exists in artifacts on infra, but it shouldn't be there.
    # Hence, we remove it here
    if "mockHyperdriveMath" in addresses_json:
        del addresses_json["mockHyperdriveMath"]

    addresses = HyperdriveAddresses(**{camel_to_snake(key): value for key, value in addresses_json.items()})
    return addresses
