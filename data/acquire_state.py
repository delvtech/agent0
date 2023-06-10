"""Script to pull on-chain hyperdrive pool data and output JSON for post-processing"""
from __future__ import annotations

import json
import os

from eth_typing import URI
from eth_utils import address
from web3.contract import Contract  # type: ignore=reportPrivateImportUsage
from web3.types import BlockData

from elfpy.utils import outputs as output_utils

from . import contract_interface

# TODO: Fix these later
# pyright: reportPrivateImportUsage=false, reportGeneralTypeIssues=false
# pyright: reportTypedDictNotRequiredAccess=false, reportUnboundVariable=false


def main(ethereum_node: URI | str, hyperdrive_abi_file_path: str, contracts_url: str, output_location: str):
    """Main entry point for accessing contract & writing pool info"""
    # pylint: disable=too-many-locals
    # get web3 provider
    web3_container = contract_interface.setup_web3(ethereum_node)
    # send a request to the local server to fetch the deployed contract addresses and
    # load the deployed Hyperdrive contract addresses from the server response
    addresses = contract_interface.fetch_addresses(contracts_url)
    # get
    with open(hyperdrive_abi_file_path, "r", encoding="UTF-8") as file:
        abi = json.load(file)["abi"]
    # get contract instance of hyperdrive
    hyperdrive_contract: Contract = web3_container.eth.contract(
        address=address.to_checksum_address(addresses.hyperdrive), abi=abi
    )
    # get pool config from hyperdrive contract
    pool_config = contract_interface.get_smart_contract_read_call(hyperdrive_contract, "getPoolConfig")
    contract_file = os.path.join(output_location, "hyperdrive_config.json")
    with open(contract_file, mode="w", encoding="UTF-8") as file:
        json.dump(pool_config, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
    # write the initial pool info
    pool_info = {}
    block: BlockData = web3_container.eth.get_block("latest")
    block_number: int = block.number
    latest_block_number: int = block_number
    latest_block_timestamp: BlockData = web3_container.eth.get_block("latest").timestamp
    block_pool_info = contract_interface.get_smart_contract_read_call(hyperdrive_contract, "getPoolInfo")
    block_pool_info.update({"timestamp": latest_block_timestamp})
    pool_info[latest_block_number] = block_pool_info
    with open(contract_file, mode="w", encoding="UTF-8") as file:
        json.dump(pool_info, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
    # monitor for new blocks & add pool info per block
    while True:
        latest_block_number: int = web3_container.eth.get_block_number()
        # if we are on a new block
        if latest_block_number != block_number:
            # Backfilling for blocks that need updating
            for block_number in range(block_number + 1, latest_block_number + 1):
                latest_block_timestamp: BlockData = web3_container.eth.get_block(
                    block_identifier=block_number
                ).timestamp
                # get pool info from hyperdrive contract
                block_pool_info = contract_interface.get_smart_contract_read_call(
                    hyperdrive_contract, "getPoolInfo", block_identifier=block_number
                )
                block_pool_info.update({"timestamp": latest_block_timestamp})
                pool_info[block_number] = block_pool_info
            contract_file = os.path.join(output_location, "hyperdrive_pool_info.json")
            with open(contract_file, mode="w", encoding="UTF-8") as file:
                json.dump(pool_info, file, indent=2, cls=output_utils.ExtendedJSONEncoder)


if __name__ == "__main__":
    ETHEREUM_NODE = "http://localhost:8545"
    ABI_FILE_PATH = "./hyperdrive_solidity/.build/IHyperdrive.json"
    CONTRACTS_URL = "http://localhost:80/addresses.json"
    OUTPUT_LOCATION = ".logging"
    main(ETHEREUM_NODE, ABI_FILE_PATH, CONTRACTS_URL, OUTPUT_LOCATION)
