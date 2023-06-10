"""Script to pull on-chain hyperdrive pool data and output JSON for post-processing"""
from __future__ import annotations

import json
import os
import time

import attr
import requests
from eth_typing import URI
from eth_utils import address
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract  # type: ignore=reportPrivateImportUsage
from web3.contract.contract import ContractFunction
from web3.datastructures import AttributeDict, MutableAttributeDict
from web3.middleware import geth_poa
from web3.types import BlockData

from elfpy.utils import apeworx_integrations as ape_utils

# TODO: Fix these later
# pyright: reportPrivateImportUsage=false, reportGeneralTypeIssues=false
# pyright: reportTypedDictNotRequiredAccess=false, reportUnboundVariable=false


class ExtendedJSONEncoder(json.JSONEncoder):
    """Overrides json encoder to handle hex inputs"""

    def default(self, o):
        if isinstance(o, HexBytes):
            return o.hex()
        if isinstance(o, (AttributeDict, MutableAttributeDict)):
            return dict(o)
        return super().default(o)


def main(ethereum_node: URI | str, hyperdrive_abi_file_path: str, contracts_url: str, output_location: str):
    """Main entry point for accessing contract & writing pool info"""
    # pylint: disable=too-many-locals

    web3 = setup_web3(ethereum_node)

    # Send a request to the local server to fetch the deployed contract addresses and
    # load the deployed Hyperdrive contract addresses from the server response
    addresses = fetch_addresses(contracts_url)

    # get contract instance of hyperdrive
    with open(hyperdrive_abi_file_path, "r", encoding="UTF-8") as file:
        abi = json.load(file)["abi"]
    hyperdrive_contract: Contract = web3.eth.contract(
        address=address.to_checksum_address(addresses.hyperdrive), abi=abi
    )

    # get pool config from hyperdrive contract
    pool_config = get_smart_contract_read_call(hyperdrive_contract, "getPoolConfig")
    contract_file = os.path.join(output_location, "hyperdrive_config.json")
    with open(contract_file, mode="w", encoding="UTF-8") as file:
        json.dump(pool_config, file, indent=2, cls=ExtendedJSONEncoder)

    # write the initial pool info
    pool_info = {}
    block: BlockData = web3.eth.get_block("latest")
    block_number: int = block.number
    latest_block_number: int = block_number
    latest_block_timestamp: BlockData = web3.eth.get_block("latest").timestamp
    block_pool_info = get_smart_contract_read_call(hyperdrive_contract, "getPoolInfo")
    block_pool_info.update({"timestamp": latest_block_timestamp})
    pool_info[latest_block_number] = block_pool_info
    with open(contract_file, mode="w", encoding="UTF-8") as file:
        json.dump(pool_info, file, indent=2, cls=ExtendedJSONEncoder)
    # monitor for new blocks & add pool info per block
    while True:
        latest_block_number: int = web3.eth.get_block_number()
        # if we are on a new block
        if latest_block_number != block_number:
            # Backfilling for blocks that need updating
            for block_number in range(block_number + 1, latest_block_number + 1):
                latest_block_timestamp: BlockData = web3.eth.get_block(block_identifier=block_number).timestamp
                # get pool info from hyperdrive contract
                block_pool_info = get_smart_contract_read_call(
                        hyperdrive_contract, "getPoolInfo", block_identifier=block_number
                )
                block_pool_info.update({"timestamp": latest_block_timestamp})
                pool_info[block_number] = block_pool_info
            contract_file = os.path.join(output_location, "hyperdrive_pool_info.json")
            with open(contract_file, mode="w", encoding="UTF-8") as file:
                json.dump(pool_info, file, indent=2, cls=ExtendedJSONEncoder)


def get_smart_contract_read_call(contract: Contract, function_name: str, **function_args):
    """Get a smart contract read call"""
    # decode ABI to get pool info variable names
    abi = contract.abi
    # TODO: Fix this up to actually decode the ABI using web3
    return_value_keys = [
        component["name"]
        for component in abi[[idx for idx in range(len(abi)) if abi[idx]["name"] == function_name][0]]["outputs"][0][
            "components"
        ]
    ]
    function: ContractFunction = contract.get_function_by_name(function_name)()
    return_values = function.call(**function_args)
    # associate pool info with the keys
    assert len(return_value_keys) == len(return_values)
    result = dict((variable_name, info) for variable_name, info in zip(return_value_keys, return_values))
    return result


def setup_web3(ethereum_node: URI | str) -> Web3:
    """Create the Web3 provider and inject a geth Proof of Authority (poa) middleware."""
    web3_container = Web3(Web3.HTTPProvider(ethereum_node))
    web3_container.middleware_onion.inject(geth_poa.geth_poa_middleware, layer=0)
    return web3_container


@attr.s
class HyperdriveAddressesJson:
    """Addresses for deployed Hyperdrive contracts."""

    # pylint: disable=too-few-public-methods

    hyperdrive: str = attr.ib()
    base_token: str = attr.ib()


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
    addresses = HyperdriveAddressesJson(
        **{ape_utils.camel_to_snake(key): value for key, value in addresses_json.items()}
    )
    return addresses


# def get_contract_instance(abi: json):
#    # Load the deployed contract addresses from the server response
#    with open(hyperdrive_abi_file_path, "r", encoding="UTF-8") as file:
#        abi = json.load(file)["abi"]
#    contract = web3.eth.contract(address=address.to_checksum_address(addresses.hyperdrive), abi=abi)


if __name__ == "__main__":
    ETHEREUM_NODE = "http://localhost:8545"
    ABI_FILE_PATH = "./hyperdrive_solidity/.build/IHyperdrive.json"
    CONTRACTS_URL = "http://localhost:80/addresses.json"
    OUTPUT_LOCATION = ".logging"
    main(ETHEREUM_NODE, ABI_FILE_PATH, CONTRACTS_URL, OUTPUT_LOCATION)
