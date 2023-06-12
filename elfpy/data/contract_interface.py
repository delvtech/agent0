"""Functions and classes for interfacing with Hyperdrive smart contracts"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

import attr
import requests
import toml
from eth_typing import BlockNumber, URI
from eth_utils import address
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import Contract, ContractEvent, ContractFunction
from web3.middleware import geth_poa
from web3.types import ABIEvent, BlockData, EventData, LogReceipt, TxReceipt

from elfpy.utils import apeworx_integrations as ape_utils
from elfpy.utils import outputs as output_utils


@attr.s
class HyperdriveAddressesJson:
    """Addresses for deployed Hyperdrive contracts."""

    # pylint: disable=too-few-public-methods

    hyperdrive: str = attr.ib()
    base_token: str = attr.ib()


def fetch_addresses(contracts_url: str) -> HyperdriveAddressesJson:
    """Fetch addresses for deployed contracts in the Hyperdrive system."""
    attempt_num = 0
    response = None
    while attempt_num < 100:
        response = requests.get(contracts_url, timeout=60)
        # Check the status code and retry the request if it fails
        if response.status_code != 200:
            logging.warning("Request failed with status code %s @ %s", response.status_code, time.ctime())
            time.sleep(10)
            continue
        attempt_num += 1
    if response is None:
        raise ConnectionError("Request failed, returning status `None`")
    if response.status_code != 200:
        raise ConnectionError(f"Request failed with status code {response.status_code} @ {time.ctime()}")
    addresses_json = response.json()
    addresses = HyperdriveAddressesJson(
        **{ape_utils.camel_to_snake(key): value for key, value in addresses_json.items()}
    )
    return addresses


def fetch_and_decode_logs(web3_container: Web3, contract: Contract, tx_receipt: TxReceipt) -> list[dict[Any, Any]]:
    """Decode logs from a transaction receipt"""
    logs = []
    if tx_receipt.get("logs"):
        for log in tx_receipt["logs"]:
            event_data, event = get_event_object(web3_container, contract, log, tx_receipt)
            if event_data and event:
                # TODO: For some reason it thinks `log` is `str` instead of `EventData`
                formatted_log = dict(event_data)
                formatted_log["event"] = event.get("name")
                formatted_log["args"] = dict(event_data["args"])
                logs.append(formatted_log)
    return logs


def fetch_transactions_for_block(
    web3_container: Web3, contract: Contract, block_number: BlockNumber
) -> list[dict[str, Any]]:
    """Fetch transactions related to the hyperdrive_address contract"""
    block: BlockData = web3_container.eth.get_block(block_number, full_transactions=True)
    transactions = block.get("transactions")
    if not transactions:
        logging.info("no transactions in block %s", block.get("number"))
        return [{}]
    decoded_transactions = []
    for transaction in transactions:
        if isinstance(transaction, HexBytes):
            logging.warning("transaction HexBytes")
            continue
        if transaction.get("to") != contract.address:
            logging.warning("transaction not from hyperdrive contract")
            continue
        transaction_dict = dict(transaction)
        # Convert the HexBytes fields to their hex representation
        tx_hash = transaction.get("hash") or HexBytes("")
        transaction_dict["hash"] = tx_hash.hex()
        # Decode the transaction input
        try:
            method, params = contract.decode_function_input(transaction["input"])
            transaction_dict["input"] = {"method": method.fn_name, "params": params}
        except ValueError:  # if the input is not meant for the contract, ignore it
            continue
        tx_receipt = web3_container.eth.get_transaction_receipt(tx_hash)
        logs = fetch_and_decode_logs(web3_container, contract, tx_receipt)
        decoded_transactions.append(
            {
                "transaction": transaction_dict,
                "logs": logs,
                "receipt": recursive_dict_conversion(tx_receipt),
            }
        )
    return decoded_transactions


def get_event_object(
    web3_container: Web3, contract: Contract, log: LogReceipt, tx_receipt: TxReceipt
) -> tuple[EventData, ABIEvent] | tuple[None, None]:
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
            event_data: EventData = contract_event.process_receipt(tx_receipt)[0]
            return event_data, event  # type: ignore
    return (None, None)


def get_block_pool_info(
    web3_container: Web3, hyperdrive_contract: Contract, block_number: BlockNumber
) -> dict[str | Any, Any]:
    """Returns the block pool info from the Hyperdrive contract"""
    block_pool_info = get_smart_contract_read_call(hyperdrive_contract, "getPoolInfo", block_identifier=block_number)
    latest_block: BlockData = web3_container.eth.get_block("latest")
    latest_block_timestamp = latest_block.get("timestamp")
    if latest_block_timestamp is None:
        raise AssertionError("Latest block has no timestamp")
    block_pool_info.update({"timestamp": latest_block_timestamp})
    return block_pool_info


def get_hyperdrive_contract(abi_file_path: str, contracts_url: str, web3_container: Web3) -> Contract:
    """Get the hyperdrive contract for a given abi"""
    addresses = fetch_addresses(contracts_url)
    # Load the ABI from the JSON file
    with open(abi_file_path, "r", encoding="UTF-8") as file:
        state_abi = json.load(file)["abi"]
    # get contract instance of hyperdrive
    hyperdrive_contract: Contract = web3_container.eth.contract(
        address=address.to_checksum_address(addresses.hyperdrive), abi=state_abi
    )
    return hyperdrive_contract


def get_smart_contract_read_call(contract: Contract, function_name: str, **function_args) -> dict[Any, Any]:
    """Get a smart contract read call"""
    # decode ABI to get pool info variable names
    abi = contract.abi
    # TODO: pyright does not like the TypedDict variables from web3,
    #   Could not access item; `key` is not a defined key in "ABIEvent",
    #   so access may result in runtime exception (reportGeneralTypeIssues)
    # TODO: Fix this up to actually decode the ABI using web3
    abi_function_index = [idx for idx in range(len(abi)) if abi[idx]["name"] == function_name][0]  # type: ignore
    abi_components = abi[abi_function_index]["outputs"][0]["components"]  # type: ignore
    return_value_keys = [component["name"] for component in abi_components]  # type: ignore
    function: ContractFunction = contract.get_function_by_name(function_name)()
    return_values = function.call(**function_args)
    # associate pool info with the keys
    assert len(return_value_keys) == len(return_values)
    result = dict((variable_name, info) for variable_name, info in zip(return_value_keys, return_values))
    return result


def hyperdrive_config_to_json(config_file: str, hyperdrive_contract: Contract) -> None:
    """Write the Hyperdrive config to a json file"""
    pool_config = get_smart_contract_read_call(hyperdrive_contract, "getPoolConfig")
    logging.info("Writing pool config.")
    with open(config_file, mode="w", encoding="UTF-8") as file:
        json.dump(pool_config, file, indent=2, cls=output_utils.ExtendedJSONEncoder)


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
