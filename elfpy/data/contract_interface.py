"""Functions and classes for interfacing with smart contracts"""
from __future__ import annotations

import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any

import attr
import requests
from eth_account import Account
from eth_account.signers.local import LocalAccount
from eth_typing import BlockNumber, ChecksumAddress, URI
from eth_utils import address
from fixedpointmath import FixedPoint
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import Contract, ContractEvent, ContractFunction
from web3.middleware import geth_poa
from web3.types import (
    ABI,
    ABIFunctionComponents,
    ABIFunctionParams,
    ABIEvent,
    BlockData,
    EventData,
    LogReceipt,
    RPCEndpoint,
    RPCResponse,
    TxReceipt,
)

from elfpy.data.db_schema import PoolConfig, PoolInfo, Transaction, WalletInfo
from elfpy.markets.hyperdrive import hyperdrive_assets

RETRY_COUNT = 10


class TestAccount:
    """Web3 account that has helper functions & associated funding source"""

    # TODO: We should be adding more methods to this class.
    # If not, we can delete it at the end of the refactor.
    # pylint: disable=too-few-public-methods

    def __init__(self, extra_entropy: str = "TEST ACCOUNT"):
        """Initialize an account"""
        self.account: LocalAccount = Account().create(extra_entropy=extra_entropy)

    @property
    def checksum_address(self) -> ChecksumAddress:
        """Return the checksum address of the account"""
        return Web3.to_checksum_address(self.account.address)


@attr.s
class HyperdriveAddressesJson:
    """Addresses for deployed Hyperdrive contracts."""

    # pylint: disable=too-few-public-methods

    base_token: str = attr.ib()
    mock_hyperdrive: str = attr.ib()
    mock_hyperdrive_math: str = attr.ib()


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

    Notes
    -----
    The geth_poa_middleware is required to connect to geth --dev or the Goerli public network.
    It may also be needed for other EVM compatible blockchains like Polygon or BNB Chain (Binance Smart Chain).
    See more `here <https://web3py.readthedocs.io/en/stable/middleware.html#proof-of-authority>`_.
    """
    if request_kwargs is None:
        request_kwargs = {}
    provider = Web3.HTTPProvider(ethereum_node, request_kwargs)
    web3 = Web3(provider)
    web3.middleware_onion.inject(geth_poa.geth_poa_middleware, layer=0)
    return web3


def set_anvil_account_balance(web3: Web3, account_address: str, amount_wei: int) -> RPCResponse:
    """Set an the account using the web3 provider

    Arguments
    ---------
    amount_wei : int
        amount_wei to fund, in wei
    """
    if not web3.is_checksum_address(account_address):
        raise ValueError(f"argument {account_address=} must be a checksum address")
    params = [account_address, hex(amount_wei)]  # account, amount
    rpc_response = web3.provider.make_request(method=RPCEndpoint("anvil_setBalance"), params=params)
    return rpc_response


def mint_tokens(token_contract: Contract, account_address: str, amount_wei: int) -> HexBytes:
    """Add funds to the account

    Arguments
    ---------
    amount_wei : int
        amount_wei to fund, in wei
    """
    tx_receipt = token_contract.functions.mint(account_address, amount_wei).transact()
    return tx_receipt


def get_account_balance_from_provider(web3: Web3, account_address: str) -> int | None:
    """Get the balance for an account deployed on the web3 provider"""
    if not web3.is_checksum_address(account_address):
        raise ValueError(f"argument {account_address=} must be a checksum address")
    rpc_response = web3.provider.make_request(method=RPCEndpoint("eth_getBalance"), params=[account_address, "latest"])
    hex_result = rpc_response.get("result")
    if hex_result is not None:
        return int(hex_result, base=16)  # cast hex to int
    return None


def load_all_abis(abi_folder: str) -> dict:
    """Load all ABI jsons given an abi_folder

    Arguments
    ---------
    abi_folder: str
        The local directory that contains all abi json
    """
    abis = {}
    abi_files = _collect_files(abi_folder)
    loaded = []
    for abi_file in abi_files:
        file_name = os.path.splitext(os.path.basename(abi_file))[0]
        with open(abi_file, mode="r", encoding="UTF-8") as file:
            data = json.load(file)
        if "abi" in data:
            abis[file_name] = data["abi"]
            loaded.append(abi_file)
        else:
            logging.warning("JSON file %s did not contain an ABI", abi_file)
    logging.info("Loaded ABI files %s", str(loaded))
    return abis


def fetch_and_decode_logs(web3: Web3, contract: Contract, tx_receipt: TxReceipt) -> list[dict[Any, Any]]:
    """Decode logs from a transaction receipt"""
    logs = []
    if tx_receipt.get("logs"):
        for log in tx_receipt["logs"]:
            event_data, event = get_event_object(web3, contract, log, tx_receipt)
            if event_data and event:
                formatted_log = dict(event_data)
                formatted_log["event"] = event.get("name")
                formatted_log["args"] = dict(event_data["args"])
                logs.append(formatted_log)
    return logs


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


def contract_function_abi_outputs(contract_abi: ABI, function_name: str) -> list[tuple[str, str]] | None:
    """Parse the function abi to get the name and type for each output"""
    function_abi = None
    # find the first function matching the function_name
    for abi in contract_abi:  # loop over each entry in the abi list
        if abi.get("name") == function_name:  # check the name
            function_abi = abi  # pull out the one with the desired name
            break
    if function_abi is None:
        logging.warning("could not find function_name=%s in contract abi", function_name)
        return None
    function_outputs = function_abi.get("outputs")
    if function_outputs is None:
        logging.warning("function abi does not specify outputs")
        return None
    if not isinstance(function_outputs, list):
        logging.warning("function abi outputs are not a sequence")
        return None
    if len(function_outputs) > 1:  # multiple unnamed vars were returned
        return_names_and_types = []
        for output in function_outputs:
            return_names_and_types.append(_get_name_and_type_from_abi(output))
    if (
        function_outputs[0].get("type") == "tuple" and function_outputs[0].get("components") is not None
    ):  # multiple named outputs were returned in a struct
        abi_components = function_outputs[0].get("components")
        if abi_components is None:
            logging.warning("function abi output componenets are not a included")
            return None
        return_names_and_types = []
        for component in abi_components:
            return_names_and_types.append(_get_name_and_type_from_abi(component))
    else:  # final condition is a single output
        return_names_and_types = [_get_name_and_type_from_abi(function_outputs[0])]
    return return_names_and_types


def smart_contract_read(contract: Contract, function_name: str, *fn_args, **fn_kwargs) -> dict[str, Any]:
    """Return from a smart contract read call

    .. todo::
        function to recursively find component names & types
        function to dynamically assign types to output variables
            would be cool if this also put stuff into FixedPoint
    """
    # get the callable contract function from function_name & call it
    function: ContractFunction = contract.get_function_by_name(function_name)(*fn_args)  # , **fn_kwargs)
    return_values = function.call(**fn_kwargs)
    if not isinstance(return_values, list):
        return_values = [return_values]
    if contract.abi:  # not all contracts have an associated ABI
        return_names_and_types = contract_function_abi_outputs(contract.abi, function_name)
        if return_names_and_types is not None:
            if len(return_names_and_types) != len(return_values):
                raise AssertionError(f"{len(return_names_and_types)=} must equal {len(return_values)=}.")
            function_return_dict = dict(
                (var_name_and_type[0], var_value)
                for var_name_and_type, var_value in zip(return_names_and_types, return_values)
            )
            return function_return_dict
    return {f"var_{idx}": value for idx, value in enumerate(return_values)}


def smart_contract_transact(
    web3: Web3, contract: Contract, function_name: str, from_account: TestAccount, *fn_args
) -> TxReceipt:
    """Execute a named function on a contract that requires a signature & gas"""
    func_handle = contract.get_function_by_name(function_name)(*fn_args)
    unsent_txn = func_handle.build_transaction(
        {
            "from": from_account.checksum_address,
            "nonce": web3.eth.get_transaction_count(from_account.checksum_address),
        }
    )
    signed_txn = from_account.account.sign_transaction(unsent_txn)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    # wait for approval to complete
    tx_receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    return tx_receipt


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
    addresses = HyperdriveAddressesJson(**{_camel_to_snake(key): value for key, value in addresses_json.items()})
    return addresses


def get_hyperdrive_contract(web3: Web3, abis: dict, addresses: HyperdriveAddressesJson) -> Contract:
    """Get the hyperdrive contract given abis

    Arguments
    ---------
    web3: Web3
        web3 provider object
    abis: dict
        A dictionary that contains all abis keyed by the abi name, returned from `load_all_abis`
    addresses: HyperdriveAddressesJson
        The block number to query from the chain

    Returns
    -------
    Contract
        The contract object returned from the query
    """
    if "IHyperdrive" not in abis:
        raise AssertionError("IHyperdrive ABI was not provided")
    state_abi = abis["IHyperdrive"]
    # get contract instance of hyperdrive
    hyperdrive_contract: Contract = web3.eth.contract(
        address=address.to_checksum_address(addresses.mock_hyperdrive), abi=state_abi
    )
    return hyperdrive_contract


def get_funding_contract(web3: Web3, abis: dict, addresses: HyperdriveAddressesJson) -> Contract:
    """Get the funding contract for a given abi
    Arguments
    ---------
    web3: Web3
        web3 provider object
    abis: dict
        A dictionary that contains all abis keyed by the abi name, returned from `load_all_abis`
    addresses: HyperdriveAddressesJson
        The block number to query from the chain

    Returns
    -------
    Contract
        The contract object returned from the query
    """
    if "ERC20Mintable" not in abis:
        raise AssertionError("ERC20 ABI for minting base tokens was not provided")
    state_abi = abis["ERC20Mintable"]
    # get contract instance of hyperdrive
    hyperdrive_contract: Contract = web3.eth.contract(
        address=address.to_checksum_address(addresses.base_token), abi=state_abi
    )
    return hyperdrive_contract


def fetch_transactions_for_block(web3: Web3, contract: Contract, block_number: BlockNumber) -> list[Transaction]:
    """
    Fetch transactions related to the contract
    Returns the block pool info from the Hyperdrive contract

    Arguments
    ---------
    web3: Web3
        web3 provider object
    hyperdrive_contract: Contract
        The contract to query the pool info from
    block_number: BlockNumber
        The block number to query from the chain

    Returns
    -------
    list[Transaction]
        A list of Transaction objects ready to be inserted into Postgres
    """
    block: BlockData = web3.eth.get_block(block_number, full_transactions=True)
    transactions = block.get("transactions")
    if not transactions:
        logging.info("no transactions in block %s", block.get("number"))
        return []
    out_transactions = []
    for transaction in transactions:
        if isinstance(transaction, HexBytes):
            logging.warning("transaction HexBytes")
            continue
        if transaction.get("to") != contract.address:
            logging.warning("transaction not from contract")
            continue
        transaction_dict: dict[str, Any] = dict(transaction)
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
        receipt: dict[str, Any] = _recursive_dict_conversion(tx_receipt)  # type: ignore

        out_transactions.append(_build_transaction_object(transaction_dict, logs, receipt))

    return out_transactions


def get_block_pool_info(web3: Web3, hyperdrive_contract: Contract, block_number: BlockNumber) -> PoolInfo:
    """
    Returns the block pool info from the Hyperdrive contract

    Arguments
    ---------
    web3: Web3
        web3 provider object
    hyperdrive_contract: Contract
        The contract to query the pool info from
    block_number: BlockNumber
        The block number to query from the chain

    Returns
    -------
    PoolInfo
        A PoolInfo object ready to be inserted into Postgres
    """
    pool_info_data_dict = smart_contract_read(hyperdrive_contract, "getPoolInfo", block_identifier=block_number)
    pool_info_data_dict: dict[Any, Any] = {
        key: _convert_scaled_value(value) for (key, value) in pool_info_data_dict.items()
    }
    current_block: BlockData = web3.eth.get_block(block_number)
    current_block_timestamp = current_block.get("timestamp")
    if current_block_timestamp is None:
        raise AssertionError("Current block has no timestamp")
    pool_info_data_dict.update({"timestamp": current_block_timestamp})
    pool_info_data_dict.update({"blockNumber": block_number})
    pool_info_dict = {}
    for key in PoolInfo.__annotations__.keys():
        # Required keys
        if key == "timestamp":
            pool_info_dict[key] = datetime.fromtimestamp(pool_info_data_dict[key])
        elif key == "blockNumber":
            pool_info_dict[key] = pool_info_data_dict[key]
        # Otherwise default to None if not exist
        else:
            pool_info_dict[key] = pool_info_data_dict.get(key, None)
    # Populating the dataclass from the dictionary
    pool_info = PoolInfo(**pool_info_dict)
    return pool_info


def get_hyperdrive_config(hyperdrive_contract: Contract) -> PoolConfig:
    """Get the hyperdrive config from a deployed hyperdrive contract.

    Arguments
    ----------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.

    Returns
    -------
    hyperdrive_config : PoolConfig
        The hyperdrive config.
    """

    hyperdrive_config: dict[str, Any] = smart_contract_read(hyperdrive_contract, "getPoolConfig")

    out_config = {}
    out_config["contractAddress"] = hyperdrive_contract.address
    out_config["baseToken"] = hyperdrive_config.get("baseToken", None)
    out_config["initializeSharePrice"] = _convert_scaled_value(hyperdrive_config.get("initializeSharePrice", None))
    out_config["positionDuration"] = hyperdrive_config.get("positionDuration", None)
    out_config["checkpointDuration"] = hyperdrive_config.get("checkpointDuration", None)
    config_time_stretch = hyperdrive_config.get("timeStretch", None)
    if config_time_stretch:
        fp_time_stretch = FixedPoint(scaled_value=config_time_stretch)
        time_stretch = float(fp_time_stretch)
        inv_time_stretch = float(1 / fp_time_stretch)
    else:
        time_stretch = None
        inv_time_stretch = None
    out_config["timeStretch"] = time_stretch
    out_config["governance"] = hyperdrive_config.get("governance", None)
    out_config["feeCollector"] = hyperdrive_config.get("feeCollector", None)
    curve_fee, flat_fee, governance_fee = hyperdrive_config.get("fees", (None, None, None))
    out_config["curveFee"] = _convert_scaled_value(curve_fee)
    out_config["flatFee"] = _convert_scaled_value(flat_fee)
    out_config["governanceFee"] = _convert_scaled_value(governance_fee)
    out_config["oracleSize"] = hyperdrive_config.get("oracleSize", None)
    out_config["updateGap"] = hyperdrive_config.get("updateGap", None)
    out_config["invTimeStretch"] = inv_time_stretch
    if out_config["positionDuration"] is not None:
        term_length = out_config["positionDuration"] / 60 / 60 / 24  # in days
    else:
        term_length = None
    out_config["termLength"] = term_length

    return PoolConfig(**out_config)


def get_wallet_info(
    hyperdrive_contract: Contract,
    base_contract: Contract,
    block_number: BlockNumber,
    transactions: list[Transaction],
) -> list[WalletInfo]:
    """Retrieves wallet information at a given block given a transaction
    Transactions are needed here to get
    (1) the wallet address of a transaction, and
    (2) the token id of the transaction

    Arguments
    ----------
    hyperdrive_contract : Contract
        The deployed hyperdrive contract instance.
    base_contract : Contract
        The deployed base contract instance
    block_number : BlockNumber
        The block number to query
    transactions : list[Transaction]
        The list of transactions to get events from

    Returns
    -------
    list[WalletInfo]
        The list of WalletInfo objects ready to be inserted into postgres
    """

    # pylint: disable=too-many-locals

    out_wallet_info = []
    for transaction in transactions:
        wallet_addr = transaction.event_operator
        token_id = transaction.event_id
        token_prefix = transaction.event_prefix
        token_maturity_time = transaction.event_maturity_time

        if wallet_addr is None:
            continue

        num_base_token_scaled = None
        for _ in range(RETRY_COUNT):
            try:
                num_base_token_scaled = base_contract.functions.balanceOf(wallet_addr).call(
                    block_identifier=block_number
                )
                break
            except ValueError:
                logging.warning("Error in getting base token balance, retrying")
                time.sleep(1)
                continue

        num_base_token = _convert_scaled_value(num_base_token_scaled)
        if (num_base_token is not None) and (wallet_addr is not None):
            out_wallet_info.append(
                WalletInfo(
                    blockNumber=block_number,
                    walletAddress=wallet_addr,
                    baseTokenType="BASE",
                    tokenType="BASE",
                    tokenValue=num_base_token,
                )
            )

        # Handle cases where these fields don't exist
        if (token_id is not None) and (token_prefix is not None):
            base_token_type = hyperdrive_assets.AssetIdPrefix(token_prefix).name
            if (token_maturity_time is not None) and (token_maturity_time > 0):
                token_type = base_token_type + "-" + str(token_maturity_time)
                maturity_time = token_maturity_time
            else:
                token_type = base_token_type
                maturity_time = None

            num_custom_token_scaled = None
            for _ in range(RETRY_COUNT):
                try:
                    num_custom_token_scaled = hyperdrive_contract.functions.balanceOf(int(token_id), wallet_addr).call(
                        block_identifier=block_number
                    )
                except ValueError:
                    logging.warning("Error in getting custom token balance, retrying")
                    time.sleep(1)
                    continue
            num_custom_token = _convert_scaled_value(num_custom_token_scaled)

            if num_custom_token is not None:
                out_wallet_info.append(
                    WalletInfo(
                        blockNumber=block_number,
                        walletAddress=wallet_addr,
                        baseTokenType=base_token_type,
                        tokenType=token_type,
                        tokenValue=num_custom_token,
                        maturityTime=maturity_time,
                    )
                )

    return out_wallet_info


def _convert_scaled_value(input_val: int | None) -> float | None:
    """
    Given a scaled value int, converts it to an unscaled value in float, while dealing with Nones

    Arguments
    ----------
    input_val: int | None
        The scaled integer value to unscale and convert to float

    Returns
    -------
    float | None
        The unscaled floating point value
    """

    # We cast to FixedPoint, then to floats to keep noise to a minimum
    # This is assuming there's no loss of precision going from Fixedpoint to float
    # Once this gets fed into postgres, postgres has fixed precision Numeric type
    if input is not None:
        return float(FixedPoint(scaled_value=input_val))
    return None


def _build_transaction_object(
    transaction_dict: dict[str, Any],
    logs: list[dict[str, Any]],
    receipt: dict[str, Any],
) -> Transaction:
    """
    Conversion function to translate output of chain queries to the Transaction object

    Arguments
    ----------
    transaction_dict : dict[str, Any]
        A dictionary representing the decoded transactions from the query
    logs: list[str, Any]
        A dictionary representing the decoded logs from the query
    receipt: dict[str, Any]
        A dictionary representing the transaction receipt from the query

    Returns
    -------
    Transaction
        A transaction object to be inserted into postgres
    """

    # Build output obj dict incrementally to be passed into Transaction
    # i.e., Transaction(**out_dict)

    # Base transaction fields
    out_dict: dict[str, Any] = {
        "blockNumber": transaction_dict["blockNumber"],
        "transactionIndex": transaction_dict["transactionIndex"],
        "nonce": transaction_dict["nonce"],
        "transactionHash": transaction_dict["hash"],
        "txn_to": transaction_dict["to"],
        "txn_from": transaction_dict["from"],
        "gasUsed": receipt["gasUsed"],
    }

    # Input solidity methods and parameters
    # TODO can the input field ever be empty or not exist?
    out_dict["input_method"] = transaction_dict["input"]["method"]
    input_params = transaction_dict["input"]["params"]
    out_dict["input_params_contribution"] = _convert_scaled_value(input_params.get("_contribution", None))
    out_dict["input_params_apr"] = _convert_scaled_value(input_params.get("_apr", None))
    out_dict["input_params_destination"] = input_params.get("_destination", None)
    out_dict["input_params_asUnderlying"] = input_params.get("_asUnderlying", None)
    out_dict["input_params_baseAmount"] = _convert_scaled_value(input_params.get("_baseAmount", None))
    out_dict["input_params_minOutput"] = _convert_scaled_value(input_params.get("_minOutput", None))
    out_dict["input_params_bondAmount"] = _convert_scaled_value(input_params.get("_bondAmount", None))
    out_dict["input_params_maxDeposit"] = _convert_scaled_value(input_params.get("_maxDeposit", None))
    out_dict["input_params_maturityTime"] = input_params.get("_maturityTime", None)
    out_dict["input_params_minApr"] = _convert_scaled_value(input_params.get("_minApr", None))
    out_dict["input_params_maxApr"] = _convert_scaled_value(input_params.get("_maxApr", None))
    out_dict["input_params_shares"] = _convert_scaled_value(input_params.get("_shares", None))

    # Assuming one TransferSingle per transfer
    # TODO Fix this below eventually
    # There can be two transfer singles
    # Currently grab first transfer single (e.g., Minting hyperdrive long, so address 0 to agent)
    # Eventually need grabbing second transfer single (e.g., DAI from agent to hyperdrive)
    event_logs = [log for log in logs if log["event"] == "TransferSingle"]
    if len(event_logs) == 0:
        event_args: dict[str, Any] = {}
        # Set args as None
    elif len(event_logs) == 1:
        event_args: dict[str, Any] = event_logs[0]["args"]
    else:
        logging.warning("Tranfer event contains multiple TransferSingle logs, selecting first")
        event_args: dict[str, Any] = event_logs[0]["args"]

    out_dict["event_value"] = _convert_scaled_value(event_args.get("value", None))
    out_dict["event_from"] = event_args.get("from", None)
    out_dict["event_to"] = event_args.get("to", None)
    out_dict["event_operator"] = event_args.get("operator", None)
    out_dict["event_id"] = event_args.get("id", None)

    # Decode logs here
    if out_dict["event_id"] is not None:
        event_prefix, event_maturity_time = hyperdrive_assets.decode_asset_id(out_dict["event_id"])
        out_dict["event_prefix"] = event_prefix
        out_dict["event_maturity_time"] = event_maturity_time

    transaction = Transaction(**out_dict)

    return transaction


def _recursive_dict_conversion(obj):
    """Recursively converts a dictionary to convert objects to hex values"""
    if isinstance(obj, HexBytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {key: _recursive_dict_conversion(value) for key, value in obj.items()}
    if hasattr(obj, "items"):
        return {key: _recursive_dict_conversion(value) for key, value in obj.items()}
    return obj


def _camel_to_snake(camel_string: str) -> str:
    """Convert camelCase to snake_case"""
    snake_string = re.sub(r"(?<!^)(?=[A-Z])", "_", camel_string)
    return snake_string.lower()


def _collect_files(folder_path: str, extension: str = ".json") -> list[str]:
    """Load all files with the given extension into a list"""
    collected_files = []
    for root, _, files in os.walk(folder_path):
        for file in files:
            if file.endswith(extension):
                file_path = os.path.join(root, file)
                collected_files.append(file_path)
    return collected_files


def _get_name_and_type_from_abi(abi_outputs: ABIFunctionComponents | ABIFunctionParams) -> tuple[str, str]:
    """Retrieve and narrow the types for abi outputs"""
    return_value_name: str | None = abi_outputs.get("name")
    if return_value_name is None:
        return_value_name = "none"
    return_value_type: str | None = abi_outputs.get("type")
    if return_value_type is None:
        return_value_type = "none"
    return (return_value_name, return_value_type)
