"""Web3 powered functions for interfacing with smart contracts"""
from __future__ import annotations

import logging
from typing import Any, Sequence

from eth_typing import BlockNumber
from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import Contract, ContractEvent, ContractFunction
from web3.types import (
    ABI,
    ABIEvent,
    ABIFunctionComponents,
    ABIFunctionParams,
    BlockData,
    EventData,
    LogReceipt,
    TxReceipt,
)

from elfpy.data.db_schema import Transaction
from elfpy.markets.hyperdrive import hyperdrive_assets

from .accounts import EthAccount
from .numeric_utils import convert_scaled_value


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
    if not isinstance(return_values, Sequence):  # could be list or tuple
        return_values = [return_values]
    if contract.abi:  # not all contracts have an associated ABI
        return_names_and_types = _contract_function_abi_outputs(contract.abi, function_name)
        if return_names_and_types is not None:
            if len(return_names_and_types) != len(return_values):
                raise AssertionError(
                    f"{len(return_names_and_types)=} must equal {len(return_values)=}."
                    f"\n{return_names_and_types=}\n{return_values=}"
                )
            function_return_dict = dict(
                (var_name_and_type[0], var_value)
                for var_name_and_type, var_value in zip(return_names_and_types, return_values)
            )
            return function_return_dict
    return {f"var_{idx}": value for idx, value in enumerate(return_values)}


def smart_contract_transact(
    web3: Web3, contract: Contract, function_name: str, from_account: EthAccount, *fn_args
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
        logs = _fetch_and_decode_logs(web3, contract, tx_receipt)
        receipt: dict[str, Any] = _recursive_dict_conversion(tx_receipt)  # type: ignore
        out_transactions.append(_build_transaction_object(transaction_dict, logs, receipt))
    return out_transactions


def _get_name_and_type_from_abi(abi_outputs: ABIFunctionComponents | ABIFunctionParams) -> tuple[str, str]:
    """Retrieve and narrow the types for abi outputs"""
    return_value_name: str | None = abi_outputs.get("name")
    if return_value_name is None:
        return_value_name = "none"
    return_value_type: str | None = abi_outputs.get("type")
    if return_value_type is None:
        return_value_type = "none"
    return (return_value_name, return_value_type)


def _contract_function_abi_outputs(contract_abi: ABI, function_name: str) -> list[tuple[str, str]] | None:
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
    if not isinstance(function_outputs, Sequence):  # could be list or tuple
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


def _recursive_dict_conversion(obj):
    """Recursively converts a dictionary to convert objects to hex values"""
    if isinstance(obj, HexBytes):
        return obj.hex()
    if isinstance(obj, dict):
        return {key: _recursive_dict_conversion(value) for key, value in obj.items()}
    if hasattr(obj, "items"):
        return {key: _recursive_dict_conversion(value) for key, value in obj.items()}
    return obj


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
    out_dict["input_params_contribution"] = convert_scaled_value(input_params.get("_contribution", None))
    out_dict["input_params_apr"] = convert_scaled_value(input_params.get("_apr", None))
    out_dict["input_params_destination"] = input_params.get("_destination", None)
    out_dict["input_params_asUnderlying"] = input_params.get("_asUnderlying", None)
    out_dict["input_params_baseAmount"] = convert_scaled_value(input_params.get("_baseAmount", None))
    out_dict["input_params_minOutput"] = convert_scaled_value(input_params.get("_minOutput", None))
    out_dict["input_params_bondAmount"] = convert_scaled_value(input_params.get("_bondAmount", None))
    out_dict["input_params_maxDeposit"] = convert_scaled_value(input_params.get("_maxDeposit", None))
    out_dict["input_params_maturityTime"] = input_params.get("_maturityTime", None)
    out_dict["input_params_minApr"] = convert_scaled_value(input_params.get("_minApr", None))
    out_dict["input_params_maxApr"] = convert_scaled_value(input_params.get("_maxApr", None))
    out_dict["input_params_shares"] = convert_scaled_value(input_params.get("_shares", None))
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
    out_dict["event_value"] = convert_scaled_value(event_args.get("value", None))
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


def _fetch_and_decode_logs(web3: Web3, contract: Contract, tx_receipt: TxReceipt) -> list[dict[Any, Any]]:
    """Decode logs from a transaction receipt"""
    logs = []
    if tx_receipt.get("logs"):
        for log in tx_receipt["logs"]:
            event_data, event = _get_event_object(web3, contract, log, tx_receipt)
            if event_data and event:
                formatted_log = dict(event_data)
                formatted_log["event"] = event.get("name")
                formatted_log["args"] = dict(event_data["args"])
                logs.append(formatted_log)
    return logs


def _get_event_object(
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
