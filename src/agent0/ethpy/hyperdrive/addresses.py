"""Helper class for storing Hyperdrive addresses"""

from __future__ import annotations

import logging
import time

import requests
from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from hyperdrivetypes.types.HyperdriveRegistry import HyperdriveRegistryContract
from hyperdrivetypes.types.IHyperdrive import IHyperdriveContract
from web3 import Web3

from .get_expected_hyperdrive_version import check_hyperdrive_version, get_minimum_hyperdrive_version


def get_hyperdrive_registry_from_artifacts(artifacts_uri: str) -> str:
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

    registry_address = addresses_json["hyperdriveRegistry"]
    return registry_address


def get_hyperdrive_addresses_from_registry(hyperdrive_registry_addr: str, web3: Web3) -> dict[str, ChecksumAddress]:
    """Fetch addresses for deployed contracts in the Hyperdrive system.

    Arguments
    ---------
    hyperdrive_registry_addr: str
        The address of the Hyperdrive registry contract.
    web3: Web3
        The instantiated Web3 instance that's connect to a chain to use.

    Returns
    -------
    dict[str, ChecksumAddress]
        A dictionary keyed by the pool name (e.g., `StETHHyperdrive_14day`)
        with a value of the address of the deployed hyperdrive pool.
    """
    # TODO
    # pylint: disable=too-many-locals

    registry_contract = HyperdriveRegistryContract.factory(w3=web3)(
        address=web3.to_checksum_address(hyperdrive_registry_addr)
    )

    # Call registry contract to get registered pools.
    num_instances = registry_contract.functions.getNumberOfInstances().call()
    hyperdrive_addresses = registry_contract.functions.getInstancesInRange(0, num_instances).call()
    # TODO pypechain needs a list input for any functions that takes a vector as an input.
    # Fix to allow for any sequence input.
    hyperdrive_infos = registry_contract.functions.getInstanceInfosWithMetadata(list(hyperdrive_addresses)).call()

    # TODO there's a bug in the registry that sets the `name` field of instances as an encoded hex string
    # We decode here if we find this case
    for info in hyperdrive_infos:
        if info.name.startswith("0x"):
            # The replace is to strip trailing 0 bytes
            info.name = HexBytes(info.name).decode("utf-8").replace("\x00", "")

    if len(hyperdrive_addresses) != len(hyperdrive_infos):
        raise AssertionError(
            f"Number of hyperdrive addresses ({len(hyperdrive_addresses)}) does not match number "
            f"of hyperdrive info ({len(hyperdrive_infos)})."
        )

    out_addresses = {}

    for address, info in zip(hyperdrive_addresses, hyperdrive_infos):
        # Check versions
        hyperdrive_version = info.version
        if not check_hyperdrive_version(hyperdrive_version):
            logging.error(
                "Hyperdrive pool at address %s version not supported (minimum %s, actual %s}).",
                address,
                get_minimum_hyperdrive_version(),
                hyperdrive_version,
            )

        if info.name not in out_addresses:
            out_addresses[info.name] = address
        else:
            raise ValueError(
                f"Hyperdrive pool with name {info.name} already exists at address {out_addresses[info.name]}."
            )

    return out_addresses


def get_hyperdrive_name(hyperdrive_address: ChecksumAddress, web3: Web3) -> str:
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

    # TODO double check hyperdrive version the name was exposed
    return hyperdrive_contract.functions.name().call()
