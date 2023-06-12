"""Script to pull on-chain transaction data and output JSON for post-processing"""
from __future__ import annotations

import json
import logging
import os
import time

import requests
import toml
from eth_utils import address
from web3 import Web3
from web3.contract.contract import Contract
from web3.middleware import geth_poa

from elfpy.data import contract_interface
from elfpy.utils import outputs as output_utils

# python `open` will infer the encoding if we do not specified, which is the behavior we want for now
# pylint: disable=unspecified-encoding

# pylint: disable=too-many-locals


def main(start_block: int, contracts_url: str, ethereum_node: str, save_dir: str, abi_file_path: str):
    """Main execution entry point"""
    # Define necessary variables/objects
    if not os.path.exists(save_dir):  # create save_dir if necessary
        os.makedirs(save_dir)
    transactions_output_file = os.path.join(save_dir, "transactions.json")
    # Load the ABI from the JSON file
    with open(abi_file_path, "r") as file:
        abi = json.load(file)["abi"]
    # Connect to the Ethereum node
    web3_container = contract_interface.setup_web3(ethereum_node)
    # send a request to the local server to fetch the deployed contract addresses and
    # load the deployed Hyperdrive contract addresses from the server response
    addresses = contract_interface.fetch_addresses(contracts_url)
    # Main loop to fetch transactions continuously
    while True:
        hyperdrive_contract: Contract = web3_container.eth.contract(
            address=address.to_checksum_address(addresses.hyperdrive), abi=abi
        )
        # Get the current block number from the Ethereum node
        current_block = web3_container.eth.block_number
        logging.info("Fetching transactions up to block %s", current_block)
        # Fetch transactions related to the hyperdrive_address contract
        transactions = contract_interface.fetch_transactions_for_block_range(
            web3_container, hyperdrive_contract, start_block, current_block
        )
        # Save the updated transactions to the output file with custom encoder
        with open(transactions_output_file, "w", encoding="UTF-8") as file:
            json.dump(transactions, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
        # Wait for 10 seconds before fetching transactions again
        time.sleep(10)


if __name__ == "__main__":
    CONTRACTS_URL = "http://localhost:80/addresses.json"
    ETHEREUM_NODE = "http://localhost:8545"
    SAVE_DIR = ".logging"
    ABI_FILE_PATH = "./hyperdrive_solidity/.build/Hyperdrive.json"
    START_BLOCK = 0
    output_utils.setup_logging(".logging/acquire_transactions.log", log_file_and_stdout=True)
    main(START_BLOCK, CONTRACTS_URL, ETHEREUM_NODE, SAVE_DIR, ABI_FILE_PATH)
