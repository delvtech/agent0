"""Script to pull on-chain hyperdrive pool data and output JSON for post-processing"""
from __future__ import annotations

import json
import time
from typing import NewType

import attr
import requests
from eth_typing import URI
from eth_utils import address
from web3 import Web3
from web3.middleware import geth_poa


def main(ethereum_node: URI | str, hyperdrive_abi_file_path: str, contracts_url: str):
    """main entry point for accessing contract & writing pool info"""
    web3 = setup_web3(ethereum_node)

    # Send a request to the local server to fetch the deployed contract addresses and
    # load the deployed Hyperdrive contract addresses from the server response
    addresses = fetch_addresses(contracts_url)

    # Load the deployed contract addresses from the server response
    with open(hyperdrive_abi_file_path, "r", encoding="UTF-8") as file:
        abi = json.load(file)["abi"]
    contract = web3.eth.contract(address=address.to_checksum_address(addresses.hyperdrive), abi=abi)
    pool_info = contract.functions.getPoolInfo()

    ## Get the current block number from the Ethereum node
    #current_block = web3.eth.block_number
    ## decode data from current_block
    #block = web3.eth.get_block(current_block, full_transactions=True)


def setup_web3(ethereum_node: URI | str) -> Web3:
    # Create the Web3 provider and inject a geth Proof of Authority (poa) middleware.
    web3 = Web3(Web3.HTTPProvider(ethereum_node))
    web3.middleware_onion.inject(geth_poa.geth_poa_middleware, layer=0)
    return web3


@attr.s
class HyperdriveAddressesJson:
    """Addresses for deployed Hyperdrive contracts."""

    hyperdrive: str = attr.ib()
    base_erc20: str = attr.ib()


def fetch_addresses(contracts_url: str) -> HyperdriveAddressesJson:
    """Fetch addresses for deployed contracts in the Hyperdrive system."""
    attempt_num = 0
    while attempt_num < 100:
        response = requests.get(contracts_url, timeout=60)
        # Check the status code and retry the request if it fails
        if response.status_code != 200:
            print(f"Request failed with status code {response.status_code} @ {time.ctime()}")
            time.sleep(10)
            continue
        attempt_num += 1
    if response.status_code != 200:
        raise ConnectionError(f"Request failed with status code {response.status_code} @ {time.ctime()}")
    addresses_json = response.json()
    addresses = HyperdriveAddressesJson(**addresses_json)

    return addresses

    # first write poolConfig


def get_contract_instance(abi: json)
    # Load the deployed contract addresses from the server response
    with open(hyperdrive_abi_file_path, "r", encoding="UTF-8") as file:
        abi = json.load(file)["abi"]
    contract = web3.eth.contract(address=address.to_checksum_address(addresses.hyperdrive), abi=abi)

if __name__ == "__main__":
    ETHEREUM_NODE = "http://localhost:8545"
    ABI_FILE_PATH = "./hyperdrive_solidity/.build/Hyperdrive.json"
    CONTRACTS_URL = "http://localhost:80/addresses.json"
    main(ETHEREUM_NODE, ABI_FILE_PATH, CONTRACTS_URL)
