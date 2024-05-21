"""Helper class for storing Hyperdrive addresses"""

from __future__ import annotations

import logging
import time
from typing import Literal, overload

import requests
from eth_typing import ChecksumAddress
from web3 import Web3

from agent0.hypertypes import HyperdriveRegistryContract, IHyperdriveContract, MockERC4626Contract
from agent0.hypertypes.utilities.conversions import camel_to_snake

from .get_expected_hyperdrive_version import get_expected_hyperdrive_version
from .transactions import get_hyperdrive_pool_config


def get_hyperdrive_addresses_from_artifacts(artifacts_uri: str) -> dict[str, ChecksumAddress]:
    """Fetch addresses for deployed contracts in the Hyperdrive system.

    Arguments
    ---------
    artifacts_uri: str
        The URI for the artifacts endpoint.

    Returns
    -------
    dict[str, ChecksumAddress]
        A dictionary that mirrors the artifacts json structure.
    """
    response = None
    for _ in range(100):
        response = requests.get(artifacts_uri, timeout=60)
        # Check the status code and retry the request if it fails
        if response.status_code != 200:
            logging.warning(
                "Request for contracts_uri=%s failed with status code %s @ %s",
                artifacts_uri,
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


@overload
def get_hyperdrive_addresses_from_registry(
    hyperdrive_registry_addr: str, web3: Web3, generate_name: Literal[True] = True
) -> dict[str, ChecksumAddress]: ...


@overload
def get_hyperdrive_addresses_from_registry(
    hyperdrive_registry_addr: str, web3: Web3, generate_name: Literal[False]
) -> dict[int, ChecksumAddress]: ...


def get_hyperdrive_addresses_from_registry(
    hyperdrive_registry_addr: str, web3: Web3, generate_name: bool = True
) -> dict[str, ChecksumAddress] | dict[int, ChecksumAddress]:
    """Fetch addresses for deployed contracts in the Hyperdrive system.

    Arguments
    ---------
    hyperdrive_registry_addr: str
        The address of the Hyperdrive registry contract.
    web3: Web3
        The instantiated Web3 instance that's connect to a chain to use.
    generate_name: bool
        If true, the key for the output will be the combination of the yield token name + position duration,
        e.g., "steth_14_day". If false, the key will be an integer index based on the order of registration.

    Returns
    -------
    dict[str, ChecksumAddress] | dict[int, ChecksumAddress]
        A dictionary keyed by either a name (if `generate_name` is true) or an index (if `generate_name` is false),
        with a value of the address of the deployed hyperdrive pool.
    """
    # TODO
    # pylint: disable=too-many-locals

    registry_contract = HyperdriveRegistryContract.factory(w3=web3)(
        address=web3.to_checksum_address(hyperdrive_registry_addr)
    )
    # Look for events from the contract
    events = registry_contract.events.HyperdriveInfoUpdated.get_logs(fromBlock=0)

    # Temporary dictionary to hold registered addresses
    # keyed by hyperdrive address, valued by an arbitrary index based on event order
    unnamed_addresses_dict: dict[ChecksumAddress, int] = {}

    last_event_block_number = 0
    for i, event in enumerate(events):
        # Sanity check making sure the fields we're expecting exist
        assert "blockNumber" in event
        assert "args" in event
        event_args = event["args"]
        assert "hyperdrive" in event_args
        assert "data" in event_args
        hyperdrive_address = web3.to_checksum_address(event_args["hyperdrive"])
        data = event_args["data"]

        # Sanity check to ensure gathered events are ordered by block number
        assert event["blockNumber"] >= last_event_block_number
        last_event_block_number = event["blockNumber"]

        # If data is 1, it's a register
        if data == 1:
            # We don't care if the key already exists, as the pool can be registered multiple times
            unnamed_addresses_dict[hyperdrive_address] = i
        # If data is 0, it's a deregister
        elif data == 0:
            assert (
                hyperdrive_address in unnamed_addresses_dict
            ), f"Unexpected deregister without corresponding register for pool {hyperdrive_address}"
            # Remove item from dictionary
            unnamed_addresses_dict.pop(hyperdrive_address)

    # Check all versions of registered pools to ensure addresses are correct
    for hyperdrive_address in list(unnamed_addresses_dict.keys()):
        success = False
        hyperdrive_contract: IHyperdriveContract = IHyperdriveContract.factory(w3=web3)(
            web3.to_checksum_address(hyperdrive_address)
        )
        try:
            hyperdrive_version = hyperdrive_contract.functions.version().call()
            expected_version = get_expected_hyperdrive_version()
            if hyperdrive_version not in expected_version:
                logging.error(
                    "Hyperdrive pool at address %s version does not match (expected %s, actual %s}).",
                    hyperdrive_address,
                    expected_version,
                    hyperdrive_version,
                )
            success = True
        except Exception as e:  # pylint: disable=broad-except
            logging.error("Hyperdrive pool at address %s version call failed: %s", hyperdrive_address, repr(e))

        # Drop from table if failed
        if not success:
            del unnamed_addresses_dict[hyperdrive_address]

    addresses = {}
    if generate_name:
        for address, index in unnamed_addresses_dict.items():
            name = generate_name_for_hyperdrive(address, web3)
            if name in addresses:
                # If the name isn't unique, we append the index to the name
                name = name + "_" + str(index)
            addresses[name] = address
    else:
        # Flip key and value
        for address, index in unnamed_addresses_dict.items():
            addresses[index] = address

    return addresses


def generate_name_for_hyperdrive(hyperdrive_address: ChecksumAddress, web3: Web3) -> str:
    """Generates a name for a given hyperdrive address. The address generated is of the form
    <vault_shares_token_symbol>_<position_duration>_day.

    Arguments
    ---------
    hyperdrive_address: ChecksumAddress
        The address of a hyperdrive pool.
    web3: Web3
        The instantiated Web3 instance that's connect to a chain to use.

    Returns
    -------
    str
        The generated name of the hyperdrive pool.
    """
    # TODO ideally we would use the HyperdriveReadInterface here, but that creates a circular
    # dependency. Hence, we get the things we need here without the interface.

    hyperdrive_contract: IHyperdriveContract = IHyperdriveContract.factory(w3=web3)(
        web3.to_checksum_address(hyperdrive_address)
    )
    pool_config = get_hyperdrive_pool_config(hyperdrive_contract)

    # Although the contract here might not be MockERC4626, we only use the symbol function
    vault_shares_token_contract: MockERC4626Contract = MockERC4626Contract.factory(w3=web3)(
        address=web3.to_checksum_address(pool_config.vault_shares_token)
    )
    vault_shares_token_symbol = vault_shares_token_contract.functions.symbol().call()

    # Convert seconds to days
    position_duration = str(pool_config.position_duration // (60 * 60 * 24))

    return vault_shares_token_symbol.lower() + "_" + position_duration + "_day"
