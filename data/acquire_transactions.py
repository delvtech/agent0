"""Script to pull on-chain transaction data and output JSON for post-processing"""
from __future__ import annotations

import json
import os
import time
from json import JSONEncoder
from types import Iterable

import requests
import toml
from eth_utils.address import to_checksum_address
from hexbytes import HexBytes
from web3 import Web3
from web3.contract import Contract
from web3.contract.contract import ContractEvent
from web3.datastructures import AttributeDict, MutableAttributeDict
from web3.middleware import geth_poa
from web3.types import EventData, LogReceipt, TxReceipt

# python `open` will infer the encoding if we do not specified, which is the behavior we want for now
# pylint: disable=unspecified-encoding

# pylint: disable=too-many-locals


class ExtendedJSONEncoder(JSONEncoder):
    """Overrides json encoder to handle hex inputs"""

    def default(self, o):
        if isinstance(o, HexBytes):
            return o.hex()
        if isinstance(o, (AttributeDict, MutableAttributeDict)):
            return dict(o)
        return super().default(o)


def save_config(config, file_path):
    """Saves the config file in TOML format"""
    with open(file_path, "w", encoding="UTF-8") as file:
        toml.dump(config, file)


def load_abi(file_path):
    """Load the Application Binary Interface (ABI) from a JSON file"""
    with open(file_path, "r") as file:
        data = json.load(file)
    return data["abi"]


def recursive_dict_conversion(obj):
    """Recursively converts a dictionary to convert objects to hex values"""
    if isinstance(obj, HexBytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {key: recursive_dict_conversion(value) for key, value in obj.items()}
    if hasattr(obj, "items"):
        return {key: recursive_dict_conversion(value) for key, value in obj.items()}
    return obj


def get_event_object(web3: Web3, contract: Contract, log: LogReceipt, tx_receipt: TxReceipt) -> Iterable[EventData]:
    """Retrieves the event object and anonymous types for a  given contract and log"""
    abi_events = [abi for abi in contract.abi if abi["type"] == "event"]
    for event in abi_events:
        # Get event signature components
        name = event["name"]
        inputs = [param["type"] for param in event["inputs"]]
        inputs = ",".join(inputs)
        # Hash event signature
        event_signature_text = f"{name}({inputs})"
        event_signature_hex = web3.keccak(text=event_signature_text).hex()
        # Find match between log's event signature and ABI's event signature
        receipt_event_signature_hex = log["topics"][0].hex()
        if event_signature_hex == receipt_event_signature_hex:
            # Decode matching log
            contract_event: ContractEvent = contract.events[event["name"]]()
            decoded_logs: Iterable[EventData] = contract_event.process_receipt(tx_receipt)
            return decoded_logs
    # for event in [e for e in dir(contract.events) if not e.startswith("_")]:
    #    event_cls = getattr(contract.events, event)
    #    if log["topics"][0] == web3_instance.keccak(text=event):
    #        return event_cls(), event_cls._anonymous_types  # pylint: disable=protected-access
    # return None, []


def fetch_and_decode_logs(web3_container: Web3, contract: Contract, tx_receipt: TxReceipt):
    """Decode logs from a transaction receipt"""
    logs = []
    if tx_receipt.get("logs"):
        for log in tx_receipt["logs"]:
            event_obj, anonymous_types = get_event_object(web3_container, contract, log, tx_receipt)
            if event_obj:
                log_data = event_obj.processLog(log)
                formatted_log = {
                    "address": log_data["address"],
                    "args": {k: str(v) for k, v in log_data["args"].items()},
                    "blockHash": log_data["blockHash"].hex(),
                    "blockNumber": log_data["blockNumber"],
                    "event": event_obj.event_name,
                    "logIndex": log_data["logIndex"],
                    "transactionIndex": log_data["transactionIndex"],
                    "transactionHash": log_data["transactionHash"].hex(),
                }
                # Decode indexed and non-indexed event params
                arg_names = [
                    arg["name"] for arg in event_obj._transaction_parser.inputs  # pylint: disable=protected-access
                ]
                formatted_topics = [(arg_names[i], topic.hex()) for i, topic in enumerate(log["topics"][1:])]
                decoded_topics = {
                    arg["name"]: web3_container.codec.decode_single(arg["type"], topic)
                    for arg, topic in zip(anonymous_types, log["topics"][1:])
                }
                formatted_log["args"].update(decoded_topics)
                formatted_log["topics"] = formatted_topics
                logs.append(formatted_log)
    return logs


def fetch_transactions(web3_container, contract, start_block, current_block):
    """Fetch transactions related to the hyperdrive_address contract"""
    transactions = []
    print(f"Processing Block Range {start_block}/{current_block}")
    for block in range(start_block, current_block):
        print(f"Processing Block {block}/{current_block}")
        block = web3_container.eth.get_block(block, full_transactions=True)
        for transaction in block["transactions"]:
            tx_dict = dict(transaction)
            # Convert the HexBytes fields to their hex representation
            tx_dict["hash"] = transaction["hash"].hex()
            # Decode the transaction input
            try:
                method, params = contract.decode_function_input(transaction["input"])
                tx_dict["input"] = {"method": method.fn_name, "params": params}
            except ValueError:  # if the input is not meant for the contract, ignore it
                continue
            tx_receipt = web3_container.eth.get_transaction_receipt(transaction["hash"])
            logs = fetch_and_decode_logs(web3_container, contract, tx_receipt)
            transactions.append(
                {"transaction": tx_dict, "logs": logs, "receipt": recursive_dict_conversion(tx_receipt)}
            )
    return transactions


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
            print(f"Request failed with status code {response.status_code} @ {time.ctime()}")
            time.sleep(10)
            continue
        # Load the deployed contract addresses from the server response
        depl_addrs = response.json()
        hyperdrive_address = depl_addrs["hyperdrive"]
        contract = web3_container.eth.contract(address=to_checksum_address(hyperdrive_address), abi=abi)
        # Load the starting block number from the config file
        with open(config_file_path, "r") as file:
            config = toml.load(file)
            starting_block = config["settings"]["startBlock"]
        # Get the current block number from the Ethereum node
        current_block = web3_container.eth.block_number
        # Fetch transactions related to the hyperdrive_address contract
        transactions = fetch_transactions(web3_container, contract, starting_block, current_block)
        # Save the updated transactions to the output file with custom encoder
        with open(transactions_output_file, "w", encoding="UTF-8") as file:
            json.dump(transactions, file, indent=2, cls=ExtendedJSONEncoder)
        # Update the starting block number in the config file
        config["settings"]["startBlock"] = current_block
        # Save the updated config data to the TOML file
        # save_config(config, config_file_path)
        # Wait for 10 seconds before fetching transactions again
        time.sleep(10)


if __name__ == "__main__":
    CONFIG_FILE_PATH = "./data/config/dataConfig.toml"
    CONTRACTS_URL = "http://localhost:80/addresses.json"
    ETHEREUM_NODE = "http://localhost:8545"
    SAVE_DIR = ".logging"
    ABI_FILE_PATH = "./hyperdrive_solidity/.build/Hyperdrive.json"
    main(CONFIG_FILE_PATH, CONTRACTS_URL, ETHEREUM_NODE, SAVE_DIR, ABI_FILE_PATH)
