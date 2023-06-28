"""Functions and classes for interfacing with smart contracts"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from typing import Any, Sequence

import attr
import requests

from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import BlockNumber, URI
from eth_utils import address
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import Contract, ContractEvent, ContractFunction
from web3.middleware import geth_poa
from web3.types import ABI, ABIEvent, BlockData, EventData, LogReceipt, TxReceipt


class FundableAccount:
    """Web3 account that has helper functions & associated funding source"""

    def __init__(
        self,
        funding_contract: Contract,
        extra_entropy: str = "TEST ACCOUNT",
        initial_supply: int = 0,
    ):
        """Initialize an account"""
        self.funding_contract: Contract = funding_contract
        self.account: LocalAccount = Account().create(extra_entropy=extra_entropy)
        self.fund_account(initial_supply)

    def fund_account(self, amount: int) -> HexBytes:
        """Add funds to the account"""
        tx_receipt = self.funding_contract.functions.mint(self.address, amount).transact()
        return tx_receipt

    @property
    def balance(self) -> int:
        """Return the balance of the account"""
        return self.funding_contract.functions.balanceOf(self.address).call()

    @property
    def address(self) -> str:
        """Return the address of the account"""
        return self.account.address


@attr.s
class HyperdriveAddressesJson:
    """Addresses for deployed Hyperdrive contracts."""

    # pylint: disable=too-few-public-methods

    base_token: str = attr.ib()
    mock_hyperdrive: str = attr.ib()
    mock_hyperdrive_math: str = attr.ib()


def camel_to_snake(camel_string: str) -> str:
    """Convert camelCase to snake_case"""
    snake_string = re.sub(r"(?<!^)(?=[A-Z])", "_", camel_string)
    return snake_string.lower()


def collect_files(folder_path: str, extension: str = ".json") -> list[dict]:
    """Load all files with the given extension into a list"""
    collected_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(extension):
                file_path = os.path.join(root, file)
                collected_files.append(file_path)
    return collected_files


def load_all_abis(abi_folder: str) -> dict:
    """Load the ABI from the JSON file"""
    abis = {}
    abi_files = collect_files(abi_folder)
    for abi_file in abi_files:
        file_name = os.path.splitext(os.path.basename(abi_file))[0]
        with open(abi_file, mode="r", encoding="UTF-8") as file:
            data = json.load(file)
        if "abi" in data:
            logging.info("Loaded ABI file %s", abi_file)
            abis[file_name] = data["abi"]
        else:
            logging.warning("JSON file %s did not contain an ABI", abi_file)
    return abis


def fetch_and_decode_logs(web3: Web3, contract: Contract, tx_receipt: TxReceipt) -> list[dict[Any, Any]]:
    """Decode logs from a transaction receipt"""
    logs = []
    if tx_receipt.get("logs"):
        for log in tx_receipt["logs"]:
            event_data, event = get_event_object(web3, contract, log, tx_receipt)
            if event_data and event:
                # TODO: For some reason it thinks `log` is `str` instead of `EventData`
                formatted_log = dict(event_data)
                formatted_log["event"] = event.get("name")
                formatted_log["args"] = dict(event_data["args"])
                logs.append(formatted_log)
    return logs


def fetch_transactions_for_block(
    web3: Web3, contract: Contract, block_number: BlockNumber
) -> list[dict[str, Any]] | None:
    """Fetch transactions related to the contract"""
    block: BlockData = web3.eth.get_block(block_number, full_transactions=True)
    transactions = block.get("transactions")
    if not transactions:
        logging.info("no transactions in block %s", block.get("number"))
        return None
    decoded_block_transactions = []
    for transaction in transactions:
        if isinstance(transaction, HexBytes):
            logging.warning("transaction HexBytes")
            continue
        if transaction.get("to") != contract.address:
            logging.warning("transaction not from contract")
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
        tx_receipt = web3.eth.get_transaction_receipt(tx_hash)
        logs = fetch_and_decode_logs(web3, contract, tx_receipt)
        decoded_block_transactions.append(
            {
                "transaction": transaction_dict,
                "logs": logs,
                "receipt": recursive_dict_conversion(tx_receipt),
            }
        )
    return decoded_block_transactions


def get_event_object(
    web3: Web3, contract: Contract, log: LogReceipt, tx_receipt: TxReceipt
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
        event_signature_hex = web3.keccak(text=event_signature_text).hex()
        # Find match between log's event signature and ABI's event signature
        receipt_event_signature_hex = log["topics"][0].hex()
        if event_signature_hex == receipt_event_signature_hex:
            # Decode matching log
            contract_event: ContractEvent = contract.events[event["name"]]()  # type: ignore
            event_data: EventData = contract_event.process_receipt(tx_receipt)[0]
            return event_data, event  # type: ignore
    return (None, None)


def get_smart_contract_read_call(contract: Contract, function_name: str, **function_args) -> dict[Any, Any]:
    """Get a smart contract read call"""
    # TODO: Fix this up to actually decode the ABI using web3
    # decode ABI to get variable names
    abi: ABI = contract.abi
    abi_function_index = [idx for idx in range(len(abi)) if abi[idx].get("name") == function_name][0]
    abi_outputs = abi[abi_function_index].get("outputs")
    if not isinstance(abi_outputs, Sequence):
        raise AssertionError("could not find outputs in the abi")
    abi_components = abi_outputs[0].get("components")
    if abi_components is None:
        raise AssertionError("could not find output components in the abi")
    return_value_keys = [component.get("name") for component in abi_components]
    # get the callable contract function from function_name & call it
    function: ContractFunction = contract.get_function_by_name(function_name)()
    return_values = function.call(**function_args)
    # associate returned values with the keys
    assert len(return_value_keys) == len(return_values)
    function_return_dict = dict((variable_name, info) for variable_name, info in zip(return_value_keys, return_values))
    return function_return_dict


def recursive_dict_conversion(obj):
    """Recursively converts a dictionary to convert objects to hex values"""
    if isinstance(obj, HexBytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {key: recursive_dict_conversion(value) for key, value in obj.items()}
    if hasattr(obj, "items"):
        return {key: recursive_dict_conversion(value) for key, value in obj.items()}
    return obj


def initialize_web3_with_http_provider(ethereum_node: URI | str, request_kwargs: dict | None = None) -> Web3:
    """Initialize a Web3 instance using an HTTP provider and inject a geth Proof of Authority (poa) middleware.

    Arguments
    ---------
    ethereum_node: URI | str
        Address of the http provider
    request_kwargs: dict
        The HTTPProvider uses the python requests library for making requests.
        If you would like to modify how requests are made,
        you can use the request_kwargs to do so.
    """
    if request_kwargs is None:
        request_kwargs = {}
    provider = Web3.HTTPProvider(ethereum_node, request_kwargs)
    web3 = Web3(provider)
    web3.middleware_onion.inject(geth_poa.geth_poa_middleware, layer=0)
    return web3


def deploy_contract(web3: Web3, contract_interface: dict) -> TxReceipt:
    """Deploy contract to an address"""
    tx_hash = (
        web3.eth.contract(
            abi=contract_interface["abi"],
            bytecode=contract_interface["bin"],
        )
        .constructor()
        .transact()
    )
    deploy_address: TxReceipt = web3.eth.get_transaction_receipt(tx_hash)["contractAddress"]
    return deploy_address


def fetch_address_from_url(contracts_url: str) -> HyperdriveAddressesJson:
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
    addresses = HyperdriveAddressesJson(**{camel_to_snake(key): value for key, value in addresses_json.items()})
    return addresses


def get_block_pool_info(web3: Web3, hyperdrive_contract: Contract, block_number: BlockNumber) -> dict[str | Any, Any]:
    """Returns the block pool info from the Hyperdrive contract"""
    block_pool_info = get_smart_contract_read_call(hyperdrive_contract, "getPoolInfo", block_identifier=block_number)
    latest_block: BlockData = web3.eth.get_block("latest")
    latest_block_timestamp = latest_block.get("timestamp")
    if latest_block_timestamp is None:
        raise AssertionError("Latest block has no timestamp")
    block_pool_info.update({"timestamp": latest_block_timestamp})
    block_pool_info.update({"blockNumber": block_number})
    return block_pool_info


def get_hyperdrive_contract(abi_file_path: str, contracts_url: str, web3: Web3) -> Contract:
    """Get the hyperdrive contract for a given abi"""
    addresses = fetch_address_from_url(contracts_url)
    # Load the ABI from the JSON file
    with open(abi_file_path, "r", encoding="UTF-8") as file:
        state_abi = json.load(file)["abi"]
    # get contract instance of hyperdrive
    hyperdrive_contract: Contract = web3.eth.contract(
        address=address.to_checksum_address(addresses.mock_hyperdrive), abi=state_abi
    )
    return hyperdrive_contract


def get_hyperdrive_config(hyperdrive_contract: Contract) -> dict:
    """Get the hyperdrive config from a deployed hyperdrive contract."""
    hyperdrive_config: dict = get_smart_contract_read_call(hyperdrive_contract, "getPoolConfig")
    hyperdrive_config["invScaledTimeStretch"] = 1 / (hyperdrive_config["timeStretch"] / 1e18)
    hyperdrive_config["termLength"] = hyperdrive_config["positionDuration"] / 60 / 60 / 24  # in days
    return hyperdrive_config
