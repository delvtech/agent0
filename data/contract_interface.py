"""Functions and classes for interfacing with Hyperdrive smart contracts"""
from __future__ import annotations

import json
import time
from typing import Iterable

import attr
import requests
import toml
from eth_typing import URI
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import ContractFunction, Contract, ContractEvent
from web3.middleware import geth_poa
from web3.types import ABIEvent, EventData, LogReceipt, TxReceipt

from elfpy.utils import apeworx_integrations as ape_utils


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


def fetch_and_decode_logs(web3_container: Web3, contract: Contract, tx_receipt: TxReceipt):
    """Decode logs from a transaction receipt"""
    logs = []
    if tx_receipt.get("logs"):
        for log in tx_receipt["logs"]:
            log_data, event = get_event_object(web3_container, contract, log, tx_receipt)
            if log_data:
                # TODO: For some reason it thinks `log` is `str` instead of `EventData`
                formatted_log = {
                    "address": [log.address for log in log_data],  # type: ignore
                    "args": [log.args for log in log_data],  # type: ignore
                    "blockHash": [log.blockHash.hex() for log in log_data],  # type: ignore
                    "blockNumber": [log.blockNumber for log in log_data],  # type: ignore
                    "event": [event["name"] for _ in log_data],  # type: ignore
                    "logIndex": [log.logIndex for log in log_data],  # type: ignore
                    "transactionIndex": [log.transactionIndex for log in log_data],  # type: ignore
                    "transactionHash": [log.transactionHash.hex() for log in log_data],  # type: ignore
                }
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


def get_event_object(
    web3_container: Web3, contract: Contract, log: LogReceipt, tx_receipt: TxReceipt
) -> tuple[Iterable[EventData], ABIEvent] | tuple[None, None]:
    """Retrieves the event object and anonymous types for a  given contract and log"""
    abi_events = [abi for abi in contract.abi if abi["type"] == "event"]  # type: ignore
    for event in abi_events:  # type: ignore
        # Get event signature components
        name = event["name"]  # type: ignore
        inputs = [param["type"] for param in event["inputs"]]  # type: ignore
        inputs = ",".join(inputs)
        # Hash event signature
        event_signature_text = f"{name}({inputs})"
        event_signature_hex = web3_container.keccak(text=event_signature_text).hex()
        # Find match between log's event signature and ABI's event signature
        receipt_event_signature_hex = log["topics"][0].hex()
        if event_signature_hex == receipt_event_signature_hex:
            # Decode matching log
            contract_event: ContractEvent = contract.events[event["name"]]()  # type: ignore
            decoded_logs: Iterable[EventData] = contract_event.process_receipt(tx_receipt)
            return decoded_logs, event
    return (None, None)


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


def load_abi(file_path):
    """Load the Application Binary Interface (ABI) from a JSON file"""
    with open(file_path, mode="r", encoding="UTF-8") as file:
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


def save_config(config, file_path):
    """Saves the config file in TOML format"""
    with open(file_path, "w", encoding="UTF-8") as file:
        toml.dump(config, file)


def setup_web3(ethereum_node: URI | str) -> Web3:
    """Create the Web3 provider and inject a geth Proof of Authority (poa) middleware."""
    web3_container = Web3(Web3.HTTPProvider(ethereum_node))
    web3_container.middleware_onion.inject(geth_poa.geth_poa_middleware, layer=0)
    return web3_container
