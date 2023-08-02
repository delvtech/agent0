"""Web3 powered functions for interfacing with smart contracts"""
from __future__ import annotations

import logging
from typing import Any, Sequence

from eth_typing import ChecksumAddress
from hexbytes import HexBytes
from web3 import Web3
from web3._utils.threads import Timeout
from web3.contract.contract import Contract
from web3.exceptions import ContractCustomError, ContractLogicError, TimeExhausted, TransactionNotFound
from web3.types import ABI, ABIFunctionComponents, ABIFunctionParams, TxParams, TxReceipt, Wei

from elfpy.eth.errors.errors import decode_error_selector_for_contract

from .accounts import EthAgent


def smart_contract_read(contract: Contract, function_name_or_signature: str, *fn_args, **fn_kwargs) -> dict[str, Any]:
    """Return from a smart contract read call

    Arguments
    ---------
    contract : web3.contract.contract.Contract
        The contract that we are reading from.
    function_name_or_signature : str
        The name of the function to query.
    *fn_args : Unknown
        The arguments passed to the contract method.
    **fn_kwargs : Unknown
        The keyword arguments passed to the contract method.

    Returns
    -------
    dict[str, Any]
        A dictionary of value names

    .. todo::
        Add better typing to the return value
        function to recursively find component names & types
        function to dynamically assign types to output variables
            would be cool if this also put stuff into FixedPoint
    """
    # get the callable contract function from function_name & call it

    if "(" in function_name_or_signature:
        function = contract.get_function_by_signature(function_name_or_signature)(*fn_args)
    else:
        function = contract.get_function_by_name(function_name_or_signature)(*fn_args)
    return_values = function.call(**fn_kwargs)
    if not isinstance(return_values, Sequence):  # could be list or tuple
        return_values = [return_values]
    if contract.abi:  # not all contracts have an associated ABI
        # NOTE: this will break if a function signature is passed.  need to update this helper
        return_names_and_types = _contract_function_abi_outputs(contract.abi, function_name_or_signature)
        if return_names_and_types is not None:
            if len(return_names_and_types) != len(return_values):
                raise AssertionError(
                    f"{len(return_names_and_types)=} must equal {len(return_values)=}."
                    f"\n{return_names_and_types=}\n{return_values=}"
                )
            function_return_dict = {}
            for var_name_and_type, var_value in zip(return_names_and_types, return_values):
                var_name = var_name_and_type[0]
                if var_name:
                    function_return_dict[var_name] = var_value
                else:
                    function_return_dict["value"] = var_value
            return function_return_dict
    return {f"value{idx}": value for idx, value in enumerate(return_values)}


def smart_contract_preview_transaction(
    contract: Contract, signer: EthAgent, function_name_or_signature: str, *fn_args
) -> dict[str, Any]:
    """Returns the values from a transaction without actually submitting the transaction.

    Arguments
    ---------
    contract : web3.contract.contract.Contract
        The contract that we are reading from.
    signer: EthAgent
        The address that would sign the transaction.
    function_name_or_signature : str
        The name of the function
    *fn_args : Unknown
        The arguments passed to the contract method.

    Returns
    -------
    dict[str, Any]
        A dictionary of value names

    .. todo::
        Add better typing to the return value
        function to recursively find component names & types
        function to dynamically assign types to output variables
            would be cool if this also put stuff into FixedPoint
    """
    # get the callable contract function from function_name & call it
    if "(" in function_name_or_signature:
        function = contract.get_function_by_signature(function_name_or_signature)(*fn_args)
    else:
        function = contract.get_function_by_name(function_name_or_signature)(*fn_args)
    return_values = function.call({"from": signer.checksum_address})
    if not isinstance(return_values, Sequence):  # could be list or tuple
        return_values = [return_values]
    if contract.abi:  # not all contracts have an associated ABI
        # NOTE: this will break if a function signature is passed.  need to update this helper
        return_names_and_types = _contract_function_abi_outputs(contract.abi, function_name_or_signature)
        if return_names_and_types is not None:
            if len(return_names_and_types) != len(return_values):
                raise AssertionError(
                    f"{len(return_names_and_types)=} must equal {len(return_values)=}."
                    f"\n{return_names_and_types=}\n{return_values=}"
                )
            function_return_dict = {}
            for var_name_and_type, var_value in zip(return_names_and_types, return_values):
                var_name = var_name_and_type[0]
                if var_name:
                    function_return_dict[var_name] = var_value
                else:
                    function_return_dict["value"] = var_value
            return function_return_dict
    return {f"value{idx}": value for idx, value in enumerate(return_values)}


async def async_wait_for_transaction_receipt(
    web3: Web3, transaction_hash: HexBytes, timeout: float = 120, poll_latency: float = 0.1
) -> TxReceipt:
    """Async version of wait_for_transaction_receipt
    This function is copied from `web3.eth.wait_for_transaction_receipt`, but using a non-blocking wait
    instead of a blocking wait

    Arguments
    ---------
    web3: Web3
        web3 provider object
    transaction_hash: HexBytes
        The hash of the transaction
    timeout: float
        The amount of time in seconds to time out the connection
    poll_latency: float
        The amount of time in seconds to wait between polls

    Returns
    -------
    TxReceipt
        The transaction receipt
    """
    try:
        with Timeout(timeout) as _timeout:
            while True:
                await _timeout.async_sleep(poll_latency)
                try:
                    tx_receipt = web3.eth.get_transaction_receipt(transaction_hash)
                except TransactionNotFound:
                    tx_receipt = None
                if tx_receipt is not None:
                    break
                await _timeout.async_sleep(poll_latency)
        return tx_receipt

    except Timeout as exc:
        raise TimeExhausted(
            f"Transaction {HexBytes(transaction_hash) !r} is not in the chain " f"after {timeout} seconds"
        ) from exc


async def async_smart_contract_transact(
    web3: Web3, contract: Contract, signer: EthAgent, function_name_or_signature: str, *fn_args
) -> TxReceipt:
    """Execute a named function on a contract that requires a signature & gas
    Copy of `smart_contract_transact`, but using async wait for `wait_for_transaction_receipt`

    Arguments
    ---------
    web3 : Web3
        web3 provider object
    contract : Contract
        Any deployed web3 contract
    signer : EthAgent
        The EthAgent that will be used to pay for the gas & sign the transaction
    function_name_or_signature : str
        This function must exist in the compiled contract's ABI
    fn_args : ordered list
        All remaining arguments will be passed to the contract function in the order received

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    try:
        if "(" in function_name_or_signature:
            func_handle = contract.get_function_by_signature(function_name_or_signature)(*fn_args)
        else:
            func_handle = contract.get_function_by_name(function_name_or_signature)(*fn_args)
        unsent_txn = func_handle.build_transaction(
            {
                "from": signer.checksum_address,
                "nonce": web3.eth.get_transaction_count(signer.checksum_address),
            }
        )
        signed_txn = signer.sign_transaction(unsent_txn)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        # TODO set poll time as a parameter
        tx_receipt = await async_wait_for_transaction_receipt(web3, tx_hash)
        return tx_receipt
    except ContractCustomError as err:
        logging.error(
            "ContractCustomError %s raised.\n function name: %s\nfunction args: %s",
            decode_error_selector_for_contract(err.args[0], contract),
            function_name_or_signature,
            fn_args,
        )

        err.message = (
            f"ContractCustomError {decode_error_selector_for_contract(err.args[0], contract)} raised.\n"
            + f"function name: {function_name_or_signature}"
            + f"\nfunction args: {fn_args}"
        )

        raise err
    except ContractLogicError as err:
        logging.error(
            "ContractLogicError:\n%s\nfunction name:%s\nfunction args: %s",
            err.message,
            function_name_or_signature,
            fn_args,
        )
        raise err


def smart_contract_transact(
    web3: Web3, contract: Contract, signer: EthAgent, function_name_or_signature: str, *fn_args
) -> TxReceipt:
    """Execute a named function on a contract that requires a signature & gas

    Arguments
    ---------
    web3 : Web3
        web3 container object
    contract : Contract
        Any deployed web3 contract
    signer : EthAgent
        The EthAgent that will be used to pay for the gas & sign the transaction
    function_name_or_signature : str
        This function must exist in the compiled contract's ABI
    fn_args : ordered list
        All remaining arguments will be passed to the contract function in the order received

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    try:
        if "(" in function_name_or_signature:
            func_handle = contract.get_function_by_signature(function_name_or_signature)(*fn_args)
        else:
            func_handle = contract.get_function_by_name(function_name_or_signature)(*fn_args)
        unsent_txn = func_handle.build_transaction(
            {
                "from": signer.checksum_address,
                "nonce": web3.eth.get_transaction_count(signer.checksum_address),
            }
        )
        signed_txn = signer.sign_transaction(unsent_txn)
        tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
        # TODO set poll time as parameter
        return web3.eth.wait_for_transaction_receipt(tx_hash)
    except ContractCustomError as err:
        error_selector = decode_error_selector_for_contract(err.args[0], contract)
        logging.error(
            "ContractCustomError %s raised.\n function name: %s\nfunction args: %s",
            error_selector,
            function_name_or_signature,
            fn_args,
        )
        raise err
    except ContractLogicError as err:
        logging.error(
            "ContractLogicError:\n%s\nfunction name:%s\nfunction args: %s",
            err.message,
            function_name_or_signature,
            fn_args,
        )
        raise err


def eth_transfer(
    web3: Web3,
    signer: EthAgent,
    to_address: ChecksumAddress,
    amount_wei: int,
    max_priority_fee: int | None = None,
) -> TxReceipt:
    """Execute a generic Ethereum transaction to move ETH from one account to another.

    Arguments
    ---------
    web3 : Web3
        web3 container object
    signer : EthAgent
        The EthAgent that will be used to pay for the gas & sign the transaction
    to_address : ChecksumAddress
        Address for where the Ethereum is going to
    amount_wei : int
        Amount to transfer, in WEI
    max_priority_fee : int
        Amount of tip to provide to the miner when a block is mined

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
    unsent_txn: TxParams = {
        "from": signer.checksum_address,
        "to": to_address,
        "value": Wei(amount_wei),
        "nonce": web3.eth.get_transaction_count(signer.checksum_address),
        "chainId": web3.eth.chain_id,
    }
    if max_priority_fee is None:
        max_priority_fee = web3.eth.max_priority_fee
    pending_block = web3.eth.get_block("pending")
    base_fee = pending_block.get("baseFeePerGas", None)
    if base_fee is None:
        raise AssertionError("The latest block does not have a baseFeePerGas")
    max_fee_per_gas = max_priority_fee + base_fee
    unsent_txn["gas"] = web3.eth.estimate_gas(unsent_txn)
    unsent_txn["maxFeePerGas"] = Wei(max_fee_per_gas)
    unsent_txn["maxPriorityFeePerGas"] = Wei(max_priority_fee)
    signed_txn = signer.sign_transaction(unsent_txn)
    tx_hash = web3.eth.send_raw_transaction(signed_txn.rawTransaction)
    return web3.eth.wait_for_transaction_receipt(tx_hash)


def _get_name_and_type_from_abi(abi_outputs: ABIFunctionComponents | ABIFunctionParams) -> tuple[str, str]:
    """Retrieve and narrow the types for abi outputs"""
    return_value_name: str | None = abi_outputs.get("name")
    if return_value_name is None:
        return_value_name = "none"
    return_value_type: str | None = abi_outputs.get("type")
    if return_value_type is None:
        return_value_type = "none"
    return (return_value_name, return_value_type)


# TODO: add ability to parse function_signature as well
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
        return return_names_and_types
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
