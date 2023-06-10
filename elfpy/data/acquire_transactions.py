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
from web3.middleware import geth_poa

from elfpy.data import contract_interface
from elfpy.utils import outputs as output_utils


# python `open` will infer the encoding if we do not specified, which is the behavior we want for now
# pylint: disable=unspecified-encoding

# pylint: disable=too-many-locals


def main(config_file_path, contracts_url, ethereum_node, save_dir, abi_file_path):
    """Main execution entry point"""
    # Define necessary variables/objects
    if not os.path.exists(save_dir):  # create save_dir if necessary
        os.makedirs(save_dir)
    transactions_output_file = os.path.join(save_dir, "transactions.json")
    # Load the ABI from the JSON file
    with open(abi_file_path, "r") as file:
        abi = json.load(file)["abi"]
    # Connect to the Ethereum node
    web3_container = Web3(Web3.HTTPProvider(ethereum_node))
    web3_container.middleware_onion.inject(geth_poa.geth_poa_middleware, layer=0)
    # Main loop to fetch transactions continuously
    while True:
        # Send a request to the local server to fetch the deployed contract addresses
        response = requests.get(contracts_url, timeout=60)
        # Check the status code and retry the request if it fails
        if response.status_code != 200:
            logging.warning("Request failed with status code %s @ %s", response.status_code, time.ctime())
            time.sleep(10)
            continue
        # Load the deployed contract addresses from the server response
        depl_addrs = response.json()
        hyperdrive_address = depl_addrs["hyperdrive"]
        contract = web3_container.eth.contract(address=address.to_checksum_address(hyperdrive_address), abi=abi)
        # Load the starting block number from the config file
        with open(config_file_path, "r") as file:
            config = toml.load(file)
            starting_block = config["settings"]["startBlock"]
        # Get the current block number from the Ethereum node
        current_block = web3_container.eth.block_number
        logging.info("Fetching transactions up to block %s", current_block)
        # Fetch transactions related to the hyperdrive_address contract
        transactions = contract_interface.fetch_transactions(web3_container, contract, starting_block, current_block)
        # Save the updated transactions to the output file with custom encoder
        with open(transactions_output_file, "w", encoding="UTF-8") as file:
            json.dump(transactions, file, indent=2, cls=output_utils.ExtendedJSONEncoder)
        # Update the starting block number in the config file
        config["settings"]["startBlock"] = current_block
        # Save the updated config data to the TOML file
        # save_config(config, config_file_path)
        # Wait for 10 seconds before fetching transactions again
        time.sleep(10)


if __name__ == "__main__":
    CONFIG_FILE_PATH = "elfpy/data/config/dataConfig.toml"
    CONTRACTS_URL = "http://localhost:80/addresses.json"
    ETHEREUM_NODE = "http://localhost:8545"
    SAVE_DIR = ".logging"
    ABI_FILE_PATH = "./hyperdrive_solidity/.build/Hyperdrive.json"
    output_utils.setup_logging(".logging/acquire_transactions.log", log_file_and_stdout=True)
    main(CONFIG_FILE_PATH, CONTRACTS_URL, ETHEREUM_NODE, SAVE_DIR, ABI_FILE_PATH)
