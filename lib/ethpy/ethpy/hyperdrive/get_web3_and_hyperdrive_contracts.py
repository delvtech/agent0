"""Helper function for getting web3 and contracts."""
from __future__ import annotations

import os

from ethpy import EthConfig
from ethpy.base import initialize_web3_with_http_provider, load_all_abis, smart_contract_read,
from web3 import Web3
from web3.contract.contract import Contract

from .addresses import HyperdriveAddresses, fetch_hyperdrive_address_from_uri


def get_web3_and_hyperdrive_contracts(
    eth_config: EthConfig, contract_addresses: HyperdriveAddresses | None = None
) -> tuple[Web3, Contract, Contract, Contract]:
    """Get the web3 container and the ERC20Base and Hyperdrive contracts.

    Arguments
    ---------
    eth_config: EthConfig
        Configuration for URIs to the rpc and artifacts.
    contract_addresses: HyperdriveAddresses | None
        Configuration for defining various contract addresses.
        Will query eth_config artifacts for addresses by default

    Returns
    -------
    tuple[Web3, Contract, Contract]
        A tuple containing:
            - The web3 container
            - The base token contract
            - The yield contract
            - The hyperdrive contract
    """
    # Initialize contract addresses if none
    if contract_addresses is None:
        contract_addresses = fetch_hyperdrive_address_from_uri(os.path.join(eth_config.artifacts_uri, "addresses.json"))

    # point to chain env
    web3 = initialize_web3_with_http_provider(eth_config.rpc_uri, reset_provider=False)
    # setup base contract interface
    abis = load_all_abis(eth_config.abi_dir)
    # set up the ERC20 contract for minting base tokens
    # TODO is there a better way to pass in base and hyperdrive abi?
    base_token_contract: Contract = web3.eth.contract(
        abi=abis["ERC20Mintable"], address=web3.to_checksum_address(contract_addresses.base_token)
    )
    # set up hyperdrive contract
    hyperdrive_contract: Contract = web3.eth.contract(
        abi=abis["IHyperdrive"],
        address=web3.to_checksum_address(contract_addresses.mock_hyperdrive),
    )

    data_provider_contract: Contract = web3.eth.contract(
        abi=abis["ERC4626DataProvider"], address=web3.to_checksum_address(contract_addresses.mock_hyperdrive)
    )
    yield_address = smart_contract_read(data_provider_contract, "pool")["value"]
    yield_contract: Contract = web3.eth.contract(
        abi=abis["MockERC4626"], address=web3.to_checksum_address(yield_address)
    )

    return web3, base_token_contract, yield_contract, hyperdrive_contract
