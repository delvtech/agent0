"""Script to pull on-chain data and output JSON for post-processing"""
from __future__ import annotations
import os
import json
import requests
import time
import toml
from web3 import Web3
from web3.middleware import geth_poa_middleware
from hexbytes import HexBytes
from json import JSONEncoder
from eth_utils import to_checksum_address


class HexBytesEncoder(JSONEncoder):
    """Overrides json encoder to handle hex inputs"""
    def default(self, obj): # pylint: disable=arguments-renamed
        if isinstance(obj, HexBytes):
            return obj.hex()
        return super().default(obj)


# Save the config data to a TOML file
def save_config(config, file_path):
    """Saves the config file to file_path"""
    with open(file_path, "w") as f:
        toml.dump(config, f)


# Load the ABI from a JSON file
def load_abi(file_path):
    with open(file_path, "r") as f:
        data = json.load(f)
    return data["abi"]


# Fetch transactions related to the HYPERDRIVE contract
def fetch_transactions(w3, contract, start_block, current_block):
    transactions = []

    print(f"Processing Block Range {start_block}/{current_block}")

    for i in range(start_block, current_block):
        print(f"Processing Block {i}/{current_block}")
        block = w3.eth.get_block(i, full_transactions=True)
        for tx in block["transactions"]:
            tx_dict = dict(tx)
            # Convert the HexBytes fields to their hex representation
            tx_dict["hash"] = tx["hash"].hex()

            # Decode the transaction input
            try:
                method, params = contract.decode_function_input(tx["input"])
                tx_dict["input"] = {"method": method.fn_name, "params": params}
            except ValueError:  # if the input is not meant for the contract, ignore it
                continue

            transactions.append(
                {
                    "transaction": tx_dict,
                }
            )
    return transactions


def main():
    # Define necessary variables/objects
    config_file_path = "./data/config/dataConfig.toml"
    ethereum_node = "http://localhost:8545"
    log_dir = ".logging"

    if not os.path.exists(log_dir):  # create log_dir if necessary
        os.makedirs(log_dir)

    transactions_output_file = os.path.join(log_dir, "transactions.json")

    # Load the ABI from the JSON file
    abi_file_path = "./hyperdrive_solidity/.build/Hyperdrive.json"
    abi = load_abi(abi_file_path)

    # Connect to the Ethereum node
    w3 = Web3(Web3.HTTPProvider(ethereum_node))
    w3.middleware_onion.inject(geth_poa_middleware, layer=0)

    # Main loop to fetch transactions continuously
    while True:
        # Send a request to the local server to fetch the deployed contract addresses
        contracts_url = "http://localhost:80/addresses.json"
        response = requests.get(contracts_url)

        # Check the status code and retry the request if it fails
        if response.status_code != 200:
            print(f"Request failed with status code {response.status_code} @ {time.ctime()}")
            time.sleep(10)
            continue

        # Load the deployed contract addresses from the server response
        depl_addrs = response.json()
        HYPERDRIVE = depl_addrs["hyperdrive"]

        contract = w3.eth.contract(address=to_checksum_address(HYPERDRIVE), abi=abi)

        # Load the starting block number from the config file
        with open(config_file_path, "r") as f:
            config = toml.load(f)
            starting_block = config["settings"]["startBlock"]

        # Get the current block number from the Ethereum node
        current_block = w3.eth.block_number

        # Fetch transactions related to the HYPERDRIVE contract
        transactions = fetch_transactions(w3, contract, starting_block, current_block)

        # Save the updated transactions to the output file with custom encoder
        with open(transactions_output_file, "w") as f:
            json.dump(transactions, f, indent=2, cls=HexBytesEncoder)

        # Update the starting block number in the config file
        config["settings"]["startBlock"] = current_block

        # Save the updated config data to the TOML file
        save_config(config, config_file_path)

        # Wait for 10 seconds before fetching transactions again
        time.sleep(10)


if __name__ == "__main__":
    main()
