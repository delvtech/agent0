"""Web3 powered functions for interfacing with smart contracts"""
from __future__ import annotations

import logging
from typing import Any, Sequence

from hexbytes import HexBytes
from web3 import Web3
from web3.contract.contract import Contract, ContractFunction
from web3.types import ABI, ABIFunctionComponents, ABIFunctionParams, TxReceipt

from .accounts import EthAccount


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
    """Execute a named function on a contract that requires a signature & gas

    Arguments
    ---------
    web3 : Web3
        web3 provider object
    contract : Contract
        any compiled web3 contract
    function_name : str
        this function must exist in the compiled contract's ABI
    from_account : EthAccount
        the EthAccount that will be used to pay for the gas & sign the transaction
    fn_args : unordered list
        all remaining arguments will be passed to the contract function in the order received

    Returns
    -------
    TxReceipt
        a TypedDict; success can be checked via tx_receipt["status"]
    """
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
